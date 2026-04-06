from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Iterable, Optional, Type

from packages.strategies.base import Strategy


class StrategyRegistry:
    """Named strategy registry for fleet construction."""

    def __init__(self, strategy_classes: Optional[Mapping[str, Type[Strategy]]] = None) -> None:
        self._strategy_classes: Dict[str, Type[Strategy]] = {}
        if strategy_classes is not None:
            for name, strategy_cls in strategy_classes.items():
                self.register(name, strategy_cls)

    def register(self, name: str, strategy_cls: Type[Strategy]) -> None:
        if not issubclass(strategy_cls, Strategy):
            raise TypeError(f"{strategy_cls.__name__} must inherit from Strategy")
        self._strategy_classes[name] = strategy_cls

    def create(self, name: str, config: Dict[str, Any]) -> Strategy:
        return self._strategy_classes[name](strategy_id=name, config=config)

    def build(self, strategy_configs: Mapping[str, Dict[str, Any]]) -> Dict[str, Strategy]:
        return {name: self.create(name, dict(config)) for name, config in strategy_configs.items()}

    def names(self) -> Iterable[str]:
        return tuple(self._strategy_classes.keys())

