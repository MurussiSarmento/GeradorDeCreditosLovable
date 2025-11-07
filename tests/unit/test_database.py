from core.database.session import get_engine, get_session
from core.database.models import Base, EmailAccount
from uuid import uuid4


def test_database_init_and_insert(tmp_path):
    # garantir criação de tabelas
    engine = get_engine()
    Base.metadata.create_all(engine)

    # inserir um registro simples
    db = get_session()
    acc = EmailAccount(
        id=f"test-id-{uuid4().hex[:8]}",
        email=f"test-{uuid4().hex[:8]}@example.com",
        account_id="acc-1",
        password_encrypted="encrypted",
        token="token",
        domain="example.com",
    )
    db.add(acc)
    db.commit()

    fetched = db.query(EmailAccount).filter_by(email=acc.email).one_or_none()
    assert fetched is not None
    assert fetched.email == acc.email