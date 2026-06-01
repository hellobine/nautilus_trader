import base64
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

_SALT_LEN = 16
_MAGIC = b"QDS1"  # 文件头标识 + 版本


class SecretStore:
    """主口令加密的凭证存储。

    文件结构（二进制）：MAGIC(4) + salt(16) + Fernet密文。
    主口令经 scrypt 派生 32 字节密钥；口令本身不落盘、不驻留除派生外的用途。
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._key: bytes | None = None  # 派生出的 Fernet key（base64）

    # ---- 内部 ----
    def _derive(self, passphrase: str, salt: bytes) -> bytes:
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        raw = kdf.derive(passphrase.encode("utf-8"))
        return base64.urlsafe_b64encode(raw)

    def _read_file(self) -> tuple[bytes, bytes] | None:
        if not os.path.exists(self._path):
            return None
        blob = open(self._path, "rb").read()
        if blob[:4] != _MAGIC:
            raise ValueError("secrets 文件格式不正确")
        salt = blob[4 : 4 + _SALT_LEN]
        cipher = blob[4 + _SALT_LEN :]
        return salt, cipher

    def _write_file(self, salt: bytes, data: dict) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        token = Fernet(self._key).encrypt(json.dumps(data).encode("utf-8"))
        with open(self._path, "wb") as f:
            f.write(_MAGIC + salt + token)
        os.chmod(self._path, 0o600)
        self._salt = salt

    # ---- 公开 ----
    def is_unlocked(self) -> bool:
        return self._key is not None

    def unlock(self, passphrase: str) -> None:
        existing = self._read_file()
        if existing is None:
            # 首次：生成新盐并初始化空库
            salt = os.urandom(_SALT_LEN)
            self._key = self._derive(passphrase, salt)
            self._write_file(salt, {})
            return
        salt, cipher = existing
        self._key = self._derive(passphrase, salt)
        self._salt = salt
        try:
            Fernet(self._key).decrypt(cipher)
        except InvalidToken as exc:
            self._key = None
            raise ValueError("主口令错误") from exc

    def load(self) -> dict:
        if not self.is_unlocked():
            raise RuntimeError("未解锁")
        existing = self._read_file()
        if existing is None:
            return {}
        _salt, cipher = existing
        return json.loads(Fernet(self._key).decrypt(cipher).decode("utf-8"))

    def _save(self, data: dict) -> None:
        if not self.is_unlocked():
            raise RuntimeError("未解锁")
        self._write_file(self._salt, data)

    def set_credential(self, name: str, cred: dict) -> None:
        data = self.load()
        data[name] = cred
        self._save(data)

    def get_credential(self, name: str) -> dict | None:
        return self.load().get(name)

    def delete_credential(self, name: str) -> None:
        data = self.load()
        data.pop(name, None)
        self._save(data)

    def initialized(self) -> bool:
        return os.path.exists(self._path)
