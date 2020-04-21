# Copyright (c) 2019, Sean Vig. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union, Callable  # noqa: F401

from libqtile.command_client import InteractiveCommandClient
from libqtile.command_graph import (
    CommandGraphCall,
    CommandGraphNode,
    SelectorType,
)
from libqtile.command_interface import CommandInterface


class LazyCall:
    def __init__(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> None:
        """The lazily evaluated command graph call

        Parameters
        ----------
        call : CommandGraphCall
            The call that is made
        args : Tuple
            The args passed to the call when it is evaluated.
        kwargs : Dict
            The kwargs passed to the call when it is evaluated.
        """
        self._call = call
        self._args = args
        self._kwargs = kwargs

        self._layout_rules = defaultdict(dict)
        self._when_floating = True
        self._filter = self._default_filter

    @property
    def selectors(self) -> List[SelectorType]:
        """The selectors for the given call"""
        return self._call.selectors

    @property
    def name(self) -> str:
        """The name of the given call"""
        return self._call.name

    @property
    def args(self) -> Tuple:
        """The args to the given call"""
        return self._args

    @property
    def kwargs(self) -> Dict:
        """The kwargs to the given call"""
        return self._kwargs

    def when(self, layout: Optional[str] = None,
             when_floating: bool = True,
             filt: Optional[Callable[['Qtile'], bool]] = None) -> 'LazyCall':
        """Filter call activation per layout or floating state

        Parameters
        ----------
        layout : str or None
            Restrict call to given layout name.
        when_floating : bool
            Call if the current window is floating.
        filt : callable(qtile object) -> bool
            Arbitrary predicate called with the Qtile object. The
            result is and-ed with `when_floating`.

        When `layout` is not ``None``, `when_floating` and `filt`
        apply only to that layout.

        Multiple calls to this method can be chained to add multiple
        per-layout rules or change global defaults.

        Examples
        --------
        .. code-block:: python
            # evaluate command only in "columns" and "monadtall" layouts
            cmd.when(layout="columns").when(layout="monadtall")

            # same as above, but do not evaluate if the
            # current window is floating in "columns" layout
            cmd.when(layout="columns", when_floating=False)\
                .when(layout="monadtall")

            # never evaluate if the current window is floating
            cmd.when(when_floating=False)

            # evaluate only in group "a"
            cmd.when(filt=lambda q: q.current_group.name == 'a')

            # evaluate only in "columns" layout when in group "a"
            # and in "monadtall" layout (any group)
            cmd.when(layout="columns",
                     filt=lambda q: q.current_group.name == 'a') \
                .when(layout="monadtall")
        """
        if layout is not None:
            self._layout_rules[layout]["when_floating"] = when_floating
            self._layout_rules[layout]["filter"] = filt or (lambda q: True)
        else:
            self._when_floating = when_floating
            self._filter = filt or self._default_filter
        return self

    def check(self, q) -> bool:
        cur_layout = q.current_layout.name

        # floating window
        if q.current_window and q.current_window.floating:
            if cur_layout in self._layout_rules:
                return self._layout_rules[cur_layout]["when_floating"] and \
                    self._layout_rules[cur_layout]["filter"](q)
            else:
                return self._when_floating and self._filter(q)

        # per-layout rules
        if cur_layout in self._layout_rules:
            return self._layout_rules[cur_layout]["filter"](q)

        # no rule, apply the global filter:
        # defaults to rejecting if some rules are set
        # but current layout is not explicitly allowed
        return self._filter(q)

    def _default_filter(self, q) -> bool:
        return not (self._layout_rules and
                    q.current_layout.name not in self._layout_rules)


class LazyCommandObject(CommandInterface):
    """A lazy loading command object

    Allows all commands and items to be resolved at run time, and returns
    lazily evaluated commands.
    """

    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> LazyCall:
        """Lazily evaluate the given call"""
        return LazyCall(call, args, kwargs)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Lazily resolve the given command"""
        return True

    def has_item(self, node: CommandGraphNode, object_type: str, item: Union[str, int]) -> bool:
        """Lazily resolve the given item"""
        return True


lazy = InteractiveCommandClient(LazyCommandObject())
