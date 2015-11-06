from unittest import TestCase
from mock import Mock
from testfixtures import compare
from mush.callpoints import CallPoint
from mush.declarations import requires, returns


class TestCallPoints(TestCase):

    def setUp(self):
        self.context = Mock()

    def test_passive_attributes(self):
        # these are managed by Modifiers
        o = object()
        point = CallPoint(o)
        compare(point.previous, None)
        compare(point.next, None)
        compare(point.labels, set())

    def test_supplied_explicitly(self):
        obj = object()
        requires  = object()
        returns = object()
        result = CallPoint(obj, requires, returns)(self.context)
        compare(result, self.context.call.return_value)
        self.context.call.assert_called_with(obj, requires, returns)

    def test_extract_from_decorations(self):
        rq = requires('foo')
        rt = returns('bar')

        @rq
        @rt
        def foo():
            return 'baz'

        result = CallPoint(foo)(self.context)
        compare(result, self.context.call.return_value)
        self.context.call.assert_called_with(foo, rq, rt)

    def test_explicit_trumps_decorators(self):
        @requires('foo')
        @returns('bar')
        def foo():
            return 'baz'

        rq = object()
        rt = object()

        result = CallPoint(foo, requires=rq, returns=rt)(self.context)
        compare(result, self.context.call.return_value)
        self.context.call.assert_called_with(foo, rq, rt)

    def test_repr_minimal(self):
        def foo(): pass
        point = CallPoint(foo)
        compare(repr(foo)+" requires() returns_result_type()", repr(point))

    def test_repr_maximal(self):
        def foo(): pass
        point = CallPoint(foo, requires('foo'), returns('bar'))
        point.labels.add('baz')
        point.labels.add('bob')
        compare(repr(foo)+" requires('foo') returns('bar') <-- baz, bob",
                repr(point))



