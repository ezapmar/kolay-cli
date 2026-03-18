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
    assert len(people) == 5
    assert people[0]["firstName"] == "Ahmet"

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
