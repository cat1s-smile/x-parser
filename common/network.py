from typing import Iterable

from requests import Session
from requests.adapters import HTTPAdapter, Retry


def retry_session(retries: int = 15,
                  backoff_factor: float = 1,
                  status_forcelist: Iterable[int] = (500, 502, 503, 504),
                  session: Session = None) -> Session:
    session = session or Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('', adapter)
    return session
