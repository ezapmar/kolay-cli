from kolay_cli.services.quiz.state import QuizState
from kolay_cli.services.quiz.engine import QuizEngine
from kolay_cli.services.quiz.renderer import Renderer
from kolay_cli.services.quiz.data_provider import MockProvider
from kolay_cli.services.quiz import get_factory
from kolay_cli.services.quiz.providers.photo_match import PhotoMatchQuestion

def test_factory_registration():
    factory = get_factory()
    assert "photo_match" in factory.available_modes()
    provider = factory.get_provider("photo_match", MockProvider())
    assert provider.name == "photo_match"

def test_mock_provider():
    provider = MockProvider()
    people = provider.list_people()
    assert len(people) == 8
    assert people[0]["firstName"] == "Ahmet"
    # New: check extended mock has education and title
    assert "educationLevel" in people[0]
    assert "title" in people[0]
    # Test new data methods
    tree = provider.get_unit_tree()
    assert len(tree) >= 3
    leaves = provider.list_leaves("2024-12-01", "2024-12-31")
    assert len(leaves) >= 1


def test_photo_match_logic():
    person = {"id": "1", "firstName": "Ahmet", "lastName": "Yılmaz", "department": {"name": "IT"}}
    distractors = [{"id": "2", "firstName": "B", "lastName": "C"}, {"id": "3", "firstName": "X", "lastName": "Y"}]
    
    q = PhotoMatchQuestion(person, distractors)
    assert q.id == "1"
    assert q.correct_answer == "Ahmet Yılmaz"
    assert "Ahmet Yılmaz" in q.choices()
    assert "B C" in q.choices()
    
    res = q.check_answer("Ahmet Yılmaz")
    assert res.is_correct is True
    assert "IT" in res.explanation
    
    res_bad = q.check_answer("B C")
    assert res_bad.is_correct is False

def test_streak_logic(tmp_path):
    import json
    from datetime import date, timedelta
    
    # Inject a temporary path getter overriding QuizState logic just for this test
    # (A simpler approach is to manipulate current_streak and last_played manually)
    state = QuizState()
    
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    # Start fresh
    state.last_played = None
    state.update_streak()
    assert state.current_streak == 1
    assert state.last_played == today
    
    # Simulate playing again today -> streak shouldn't increase
    state.update_streak()
    assert state.current_streak == 1 
    
    # Simulate played yesterday
    state.last_played = yesterday
    state.update_streak()
    assert state.current_streak == 2
    assert state.last_played == today


def test_rank_system():
    from kolay_cli.services.quiz.state import _calculate_rank
    assert _calculate_rank(0) == "Çaylak İzci"
    assert _calculate_rank(9) == "Çaylak İzci"
    assert _calculate_rank(10) == "Genç Müfettiş"
    assert _calculate_rank(25) == "Kıdemli Müfettiş"
    assert _calculate_rank(50) == "Dedektif"
    assert _calculate_rank(100) == "Veri Sherlock'u"
    assert _calculate_rank(999) == "Veri Sherlock'u"


def test_state_add_points():
    state = QuizState()
    assert state.total_case_points == 0
    assert state.rank == "Çaylak İzci"
    state.add_points(15)
    assert state.total_case_points == 15
    assert state.rank == "Genç Müfettiş"
    state.add_points(50)
    assert state.rank == "Dedektif"


def test_education_champion_provider():
    from kolay_cli.services.quiz.providers.education_champion import EducationChampionProvider
    provider = EducationChampionProvider(data_provider=MockProvider())
    questions = provider.generate(1, set())
    # Mock has dept Mühendislik with 2 postgrads out of 3 — should generate a question
    assert len(questions) >= 1
    q = questions[0]
    assert q.correct_answer in q.choices()
    result = q.check_answer(q.correct_answer)
    assert result.is_correct is True
    result_bad = q.check_answer("Yanlış Departman")
    assert result_bad.is_correct is False


def test_unique_title_provider():
    from kolay_cli.services.quiz.providers.unique_title import UniqueTitleProvider
    provider = UniqueTitleProvider(data_provider=MockProvider())
    questions = provider.generate(3, set())
    assert len(questions) >= 1
    q = questions[0]
    assert q.correct_answer in q.choices()
    assert len(q.choices()) == 4
    result = q.check_answer(q.correct_answer)
    assert result.is_correct is True


def test_december_exodus_provider():
    from kolay_cli.services.quiz.providers.december_exodus import (
        DecemberExodusProvider, _is_counted_leave, _all_available_months
    )
    # Test the normalised leave filter
    assert _is_counted_leave("Yıllık İzin") is True
    assert _is_counted_leave("Uzaktan Çalışma") is True
    assert _is_counted_leave("Hastalık İzni") is False

    # Test month range generation
    months = _all_available_months("2021-01-15")
    assert len(months) > 12          # at least 12 months
    assert months[0] == (2021, 1)    # starts at start date's month

    provider = DecemberExodusProvider(data_provider=MockProvider())
    questions = provider.generate(3, set())
    assert len(questions) >= 1
    q = questions[0]
    # ID format: leave_time_machine_YYYY_MM
    assert q.id.startswith("leave_time_machine_")
    # Real answer is one of the choices
    assert q.correct_answer in q.choices()
    # Answer is numeric string
    assert int(q.correct_answer) > 0
    # Correct answer is correct
    result = q.check_answer(q.correct_answer)
    assert result.is_correct is True
    # Wrong answer fails
    wrong = next(c for c in q.choices() if c != q.correct_answer)
    assert q.check_answer(wrong).is_correct is False



def test_hint_masking():
    from kolay_cli.services.quiz.renderer import _mask_answer
    assert _mask_answer("Ahmet Yılmaz") == "A**** Y*****"
    assert _mask_answer("Mühendislik") == "M**********"
    assert _mask_answer("A") == "A"
    assert _mask_answer("Veri Dedektifi") == "V*** D********"

