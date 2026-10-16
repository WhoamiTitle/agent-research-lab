from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class Owner:
    user_id: int = field(repr=False)

    def permits(self, sender_id: int | None, *, private_chat: bool) -> bool:
        return private_chat and sender_id == self.user_id
