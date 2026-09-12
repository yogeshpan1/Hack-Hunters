from app.demo_expansion import _cohort_name, _synthetic_student_name


def test_islington_group_labels_follow_programme_conventions():
    assert _cohort_name(1, 1) == "C1"
    assert _cohort_name(1, 3) == "C3"
    assert _cohort_name(2, 1) == "AI7"
    assert _cohort_name(3, 1) == "NT1"
    assert _cohort_name(5, 1) == "B1"
    assert _cohort_name(6, 1) == "B4"
    assert _cohort_name(20, 1) == "MSc-CTI1"


def test_generated_planning_profiles_use_name_like_values():
    first = _synthetic_student_name(0)
    later = _synthetic_student_name(73)
    assert len(first.split()) == 2
    assert len(later.split()) == 2
    assert first != later
