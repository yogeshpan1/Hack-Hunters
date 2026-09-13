"""Readiness and streamed progress from real solver work; no timer-based stages."""
import json
from queue import Queue
from threading import Thread, BoundedSemaphore
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from .auth import current_user, require
from .db import get_db, MongoSession
from .schemas import RunInput
from .scheduling import snapshot, enriched
from .optimization_service import calculate_run

router=APIRouter(prefix='/api')
slots=BoundedSemaphore(2)


def readiness(data):
    checks=[]
    for key,label in [('faculty','Faculty configured'),('rooms','Rooms configured'),('modules','Modules mapped'),('cohorts','Cohorts mapped'),('sessions','Teaching sessions configured')]:
        checks.append({'key':key,'label':label,'ready':bool(data[key]),'detail':f'{len(data[key])} records available'})
    missing=[]
    for session in enriched(data):
        if not any(r['active'] and r['capacity']>=session['size'] and r['kind']==session['room_type'] and set(session['resources'])<=set(r['equipment']) and ('Computers' not in session['resources'] or r['pc_count']>=session['size']) for r in data['rooms']):
            missing.append(session['code'])
    checks.append({'key':'resources','label':'Required resources available','ready':not missing,'detail':', '.join(sorted(set(missing))) or 'At least one room meets each assignment’s resource requirements. Time availability is checked by the solver.'})
    return {'ready':all(c['ready'] for c in checks),'checks':checks}


@router.get('/readiness')
def get_readiness(db=Depends(get_db),user=Depends(current_user)):
    require(user,['RTE'])
    return readiness(snapshot(db))


@router.post('/optimization/stream')
def stream(body:RunInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,['RTE'])
    if not slots.acquire(blocking=False): raise HTTPException(429,'The solver is busy. Try again after the current calculation.')
    database=db.database
    messages=Queue()
    def work():
        try:
            with MongoSession(database) as session:
                check=readiness(snapshot(session))
                if not check['ready']:
                    messages.put({'type':'error','detail':'Complete the data readiness checks before optimization.','readiness':check})
                    return
                def progress(stage,label): messages.put({'type':'stage','stage':stage,'label':label,'status':'running'})
                result=calculate_run(body,session,user,progress)
                messages.put({'type':'result','run':result})
        except HTTPException as exc:
            messages.put({'type':'error','detail':exc.detail})
        except Exception:
            # Never serialize database exceptions: connection URIs may contain credentials.
            messages.put({'type':'error','detail':'The solver could not complete this operation. Check MongoDB and retry.'})
        finally:
            messages.put(None)
            slots.release()
    Thread(target=work,daemon=True).start()
    def events():
        while True:
            message=messages.get()
            if message is None: break
            yield json.dumps(message)+'\n'
    return StreamingResponse(events(),media_type='application/x-ndjson',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
