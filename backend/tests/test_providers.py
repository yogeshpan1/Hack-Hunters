import httpx
from app import providers
from app.models import Email
from conftest import sign_in


def test_disabled_services_make_no_requests(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER","structured")
    monkeypatch.setenv("EMAIL_PROVIDER","demo")
    monkeypatch.setattr(providers.httpx,"post",lambda *a,**k: (_ for _ in ()).throw(AssertionError("Unexpected network")))
    assert providers.normalize_question("Find rooms",[] )==("Find rooms",False)
    assert not providers.provider_status()["email_enabled"]


def test_ai_rewrites_question_and_falls_back(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER","groq");monkeypatch.setenv("GROQ_API_KEY","test")
    def respond(url,**kwargs):
        assert "database_results" not in str(kwargs)
        return httpx.Response(200,json={"choices":[{"message":{"content":'{"query":"Which faculty has the heaviest workload?"}'}}]},request=httpx.Request("POST",url))
    monkeypatch.setattr(providers.httpx,"post",respond)
    assert providers.normalize_question("Who teaches most?",[])[1]
    monkeypatch.setattr(providers.httpx,"post",lambda *a,**k: (_ for _ in ()).throw(httpx.ConnectError("secret provider error")))
    assert providers.normalize_question("Who teaches most?",[])==("Who teaches most?",False)


def test_live_email_is_audited_and_cannot_be_sent_twice(registrar,db,monkeypatch):
    email=Email(recipient="test@example.test",subject="Review",body="Test message")
    db.add(email);db.commit()
    calls=[]
    monkeypatch.setattr(providers,"send_reviewed_email",lambda obj: calls.append(obj.id) or "receipt-test")
    url=f"/api/emails/{email.id}/send-live"
    assert registrar.post(url).json()["status"]=="Accepted by Resend"
    assert registrar.post(url).status_code==200
    assert calls==[email.id]
    assert registrar.put(f"/api/emails/{email.id}",json={"subject":"Changed","body":"Changed","action":"draft"}).status_code==409
    assert any(r["action"]=="EMAIL LIVE SEND" and r["actor"] for r in registrar.get('/api/audit').json())


def test_provider_failure_preserves_draft(registrar,db,monkeypatch):
    email=Email(recipient="test@example.test",subject="Review",body="Test")
    db.add(email);db.commit()
    monkeypatch.setattr(providers,"send_reviewed_email",lambda obj: (_ for _ in ()).throw(ValueError("Delivery could not be confirmed")))
    assert registrar.post(f"/api/emails/{email.id}/send-live").status_code==502
    assert next(r for r in registrar.get('/api/emails').json() if r['id']==email.id)['status']=='Draft'


def test_live_email_requires_registrar(client):
    sign_in(client,'student')
    assert client.post('/api/emails/1/send-live').status_code==403


def test_resend_uses_stable_idempotency_key(monkeypatch):
    monkeypatch.setenv('EMAIL_PROVIDER','resend');monkeypatch.setenv('RESEND_API_KEY','test');monkeypatch.setenv('RESEND_FROM_EMAIL','sender@example.test')
    keys=[]
    def respond(url,**kwargs):
        keys.append(kwargs['headers']['Idempotency-Key'])
        return httpx.Response(200,json={'id':'receipt'},request=httpx.Request('POST',url))
    monkeypatch.setattr(providers.httpx,'post',respond)
    email=Email(id=17,recipient='test@example.test',subject='Subject',body='Body')
    assert providers.send_reviewed_email(email)=='receipt'
    providers.send_reviewed_email(email)
    assert keys[0]==keys[1]
