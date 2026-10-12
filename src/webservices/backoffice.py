"""Read methods for the Backoffice webservice (``Backoffice.asmx``).

Useful before a migration: documents still in the back-office workflow are not
booked yet, and open questions mean the books are not final. Both responses are
untyped and undocumented; they are returned as plain data.
"""

from __future__ import annotations

from ..parsing import plain
from ..service import YukiService, require_text
from ..record import YukiRecord


class BackofficeService(YukiService):
    """Read data from ``Backoffice.asmx``."""

    service_name = "Backoffice"

    def workflow(self, administration_id: str):
        """Documents Yuki could not process automatically and that wait for the accountant."""

        return plain(self.invoke("GetWorkflow", administrationID=require_text(administration_id, "administration_id")))

    def outstanding_questions(self, administration_id: str):
        """Open back-office questions of the administration."""

        return plain(
            self.invoke("GetOutstandingQuestions", administrationID=require_text(administration_id, "administration_id"))
        )

class Workflow(YukiRecord):
    """Documents waiting in the back-office workflow (``GetWorkflow``, one call). Field: ``data``."""

    def get(self) -> None:
        self._set(BackofficeService(self.client_credentials).workflow(self.administration_id))

    @property
    def data(self):
        return self._value


class OutstandingQuestions(YukiRecord):
    """Open back-office questions (``GetOutstandingQuestions``, one call). Field: ``data``."""

    def get(self) -> None:
        self._set(BackofficeService(self.client_credentials).outstanding_questions(self.administration_id))

    @property
    def data(self):
        return self._value
