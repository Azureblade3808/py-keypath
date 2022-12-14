from __future__ import annotations

from threading import Thread
from time import sleep

import pytest

from ._core import *


class TestCase:
    def test(self) -> None:
        class A(KeyPathSupporting):
            b: B

            def __init__(self) -> None:
                self.b = B()

        class B(KeyPathSupporting):
            c: int

            def __init__(self) -> None:
                self.c = 0

        a = A()
        key_path = KeyPath.of(a.b.c)
        assert key_path == KeyPath(target=a, keys=("b", "c"))
        assert key_path() == 0

        a.b.c = 1
        assert key_path() == 1

    def test_cycle_reference(self) -> None:
        class A(KeyPathSupporting):
            a: A
            b: B

            def __init__(self) -> None:
                self.a = self
                self.b = B()

        class B(KeyPathSupporting):
            b: B
            c: C

            def __init__(self) -> None:
                self.b = self
                self.c = C()

        class C:
            pass

        a = A()
        assert KeyPath.of(a.a.b.b.c) == KeyPath(target=a, keys=("a", "b", "b", "c"))

    def test_common_mistakes(self) -> None:
        class A(KeyPathSupporting):
            b: B

            def __init__(self) -> None:
                self.b = B()

        class B(KeyPathSupporting):
            c: C

            def __init__(self) -> None:
                self.c = C()

        class C:
            pass

        a = A()

        with pytest.raises(Exception):
            # Not even accessed a single member.
            _ = KeyPath.of(a)

        with pytest.raises(Exception):
            # Used something that is not a member chain.
            _ = KeyPath.of(a.b.c is not None)

        with pytest.raises(Exception):
            # Called the same `KeyPath.of` more than once.
            of = KeyPath.of
            _ = of(a.b.c)
            _ = of(a.b.c)

    def test_error_handling(self) -> None:
        class A(KeyPathSupporting):
            b: B

            def __init__(self) -> None:
                self.b = B()

        class B(KeyPathSupporting):
            c: C

            def __init__(self) -> None:
                self.c = C()

        class C:
            pass

        a = A()

        with pytest.raises(AttributeError):
            # Access something that doesn't exist.
            _ = KeyPath.of(a.b.c.d)  # type: ignore

        # With above exception caught, normal code should run correctly.
        key_path = KeyPath.of(a.b.c)
        assert key_path == KeyPath(target=a, keys=("b", "c"))

    def test_threading(self) -> None:
        class A(KeyPathSupporting):
            b: B

            def __init__(self) -> None:
                self.b = B()

        class B(KeyPathSupporting):
            c: C

            def __init__(self) -> None:
                self.c = C()

        class C:
            pass

        a = A()
        key_path_list: list[KeyPath] = []

        def f() -> None:
            sleep(1)
            key_path = KeyPath.of(a.b.c)
            key_path_list.append(key_path)

        threads = [Thread(target=f) for _ in range(1000)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(key_path_list) == 1000
        assert all(
            key_path == KeyPath(target=a, keys=("b", "c")) for key_path in key_path_list
        )

    def test_internal_reference(self) -> None:
        class C(KeyPathSupporting):
            @property
            def v0(self) -> int:
                return self.v1.v2

            @property
            def v1(self) -> C:
                return self

            @property
            def v2(self) -> int:
                return 0

        c = C()
        assert KeyPath.of(c.v0) == KeyPath(target=c, keys=("v0",))
