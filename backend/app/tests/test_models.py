import uuid
from app.models.user import User

def test_user_model_initialization():
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        full_name="Anand Kumar",
        email="anand@example.com",
        password_hash="argon2_hashed_secret",
        role="candidate"
    )

    assert user.id == user_id
    assert user.full_name == "Anand Kumar"
    assert user.email == "anand@example.com"
    assert user.role == "candidate"
    assert repr(user) == "<User anand@example.com (candidate)>"
