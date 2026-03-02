from unittest.mock import patch

import pytest

from app.auth import is_admin
from app.config import settings


def test_is_admin_with_admin_operator_env():
    with patch.object(settings, "admin_operator", "Caio"), \
         patch.object(settings, "operators", "Caio,João,Vitória"):
        assert is_admin("Caio") is True
        assert is_admin("João") is False
        assert is_admin("Vitória") is False


def test_is_admin_falls_back_to_first_operator():
    with patch.object(settings, "admin_operator", ""), \
         patch.object(settings, "operators", "Caio,João"):
        assert is_admin("Caio") is True
        assert is_admin("João") is False


def test_is_admin_no_operators_everyone_is_admin():
    with patch.object(settings, "admin_operator", ""), \
         patch.object(settings, "operators", ""):
        assert is_admin(None) is True
        assert is_admin("Anyone") is True
