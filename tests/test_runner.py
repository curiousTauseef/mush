from unittest import TestCase

from mock import Mock, call
from testfixtures import ShouldRaise, StringComparison as S, compare

from mush import Periods, Runner, requires, first, last

class RunnerTests(TestCase):

    def test_simple(self):
        m = Mock()        
        def job():
            m.job()
            
        runner = Runner()
        runner.add(job)
        runner()

        compare([
                call.job()
                ], m.mock_calls)

    def test_constructor(self):
        m = Mock()        
        def job1():
            m.job1()
        def job2():
            m.job2()
            
        runner = Runner(job1, job2)
        runner()

        compare([
                call.job1(),
                call.job2(),
                ], m.mock_calls)

    def test_context_declarative(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass

        t1 = T1()
        t2 = T2()

        def job1():
            m.job1()
            return t1

        @requires(T1)
        def job2(obj):
            m.job2(obj)
            return t2

        @requires(T2)
        def job3(obj):
            m.job3(obj)

        runner = Runner(job1, job2, job3)
        runner()
        
        compare([
                call.job1(),
                call.job2(t1),
                call.job3(t2),
                ], m.mock_calls)


    def test_context_imperative(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass

        t1 = T1()
        t2 = T2()

        def job1():
            m.job1()
            return t1

        def job2(obj):
            m.job2(obj)
            return t2

        def job3(t2_):
            m.job3(t2_)

        # imperative config trumps declarative
        @requires(T1)
        def job4(t2_):
            m.job4(t2_)
            
        runner = Runner()
        runner.add(job1)
        runner.add(job2, T1)
        runner.add(job3, t2_=T2)
        runner.add(job4, T2)
        runner()
        
        compare([
                call.job1(),
                call.job2(t1),
                call.job3(t2),
                call.job4(t2),
                ], m.mock_calls)


    def test_returns_type_mapping(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass
        t = T1()

        def job1():
            m.job1()
            return {T2:t}

        @requires(T2)
        def job2(obj):
            m.job2(obj)

        Runner(job1, job2)()
        
        compare([
                call.job1(),
                call.job2(t),
                ], m.mock_calls)

    def test_returns_tuple(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass

        t1 = T1()
        t2 = T2()

        def job1():
            m.job1()
            return t1, t2

        @requires(T1, T2)
        def job2(obj1, obj2):
            m.job2(obj1, obj2)

        Runner(job1, job2)()
        
        compare([
                call.job1(),
                call.job2(t1, t2),
                ], m.mock_calls)

    def test_returns_list(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass

        t1 = T1()
        t2 = T2()

        def job1():
            m.job1()
            return [t1, t2]

        @requires(obj1=T1, obj2=T2)
        def job2(obj1, obj2):
            m.job2(obj1, obj2)

        Runner(job1, job2)()
        
        compare([
                call.job1(),
                call.job2(t1, t2),
                ], m.mock_calls)

    def test_missing_from_context(self):
        # make sure exception is helpful
        class T(object): pass

        @requires(T)
        def job(arg):
            pass # pragma: nocover

        runner = Runner(job)
        with ShouldRaise(KeyError(
                S("'No T in context' attempting to call <function job at \w+>")
                )):
            runner()

    def test_classes(self):
        m = Mock()        
        class T0(object): pass
        class T1(object): pass
        class T2(object): pass
        t1 = T1()
        t2 = T2()
        
        class C1(object):

            def __init__(self):
                m.C1.__init__()
                             
            def meth(self):
                m.C1.method()
                return t1

            
        @requires(T1)
        class C2(object):

            def __init__(self, obj):
                m.C2.init(obj)

            @requires(T0)
            def meth1(self, obj):
                m.C2.meth1(type(obj))
                return t2

            @requires(T2)
            def meth2(self, obj):
                m.C2.meth2(obj)

        class C3(object):

            @requires(T2)
            def __call__(self, obj):
                m.C3.call(obj)

        runner = Runner(
            T0,
            C1.meth,
            C2.meth1,
            C2.meth2,
            )
        runner.add(C3.__call__)
        runner()
        
        compare([
                call.C2.init(t1),
                call.C2.meth1(T0),
                call.C2.meth2(t2),
                call.C3.call(t2),
                ], m.mock_calls)
        
    def test_context_manager(self):
        m = Mock()
        
        class CM1(object):
            def __enter__(self):
                m.cm1.enter()
            def __exit__(self, type, obj, tb):
                m.cm1.exit(type, obj)
                return True

        class CM2(object):
            def __enter__(self):
                m.cm2.enter()
            def __exit__(self, type, obj, tb):
                m.cm2.exit(type, obj)

        @requires(CM1)
        def func1(obj):
            m.func1(type(obj))

        @requires(CM1, CM2)
        def func2(obj1, obj2):
            m.func2(type(obj1), type(obj2))
            
        runner = Runner(
            CM1,
            CM2,
            func1,
            func2,
            )
        
        runner()
        compare([
                call.cm1.enter(),
                call.cm2.enter(),
                call.func1(CM1),
                call.func2(CM1, CM2),
                call.cm2.exit(None, None),
                call.cm1.exit(None, None)
                ], m.mock_calls)
        
        # now check with an exception
        m.reset_mock()
        m.func2.side_effect = e = Exception()
        runner()
        compare([
                call.cm1.enter(),
                call.cm2.enter(),
                call.func1(CM1),
                call.func2(CM1, CM2),
                call.cm2.exit(Exception, e),
                call.cm1.exit(Exception, e)
                ], m.mock_calls)
        
    def test_marker_interfaces(self):
        # return {Type:None}
        # don't pass when a requirement is for a type but value is None
        class Marker(object): pass

        m = Mock()
        
        def setup():
            m.setup()
            return {Marker:None}

        @requires(Marker)
        def use():
            m.use()

        Runner(use, setup)()
        
        compare([
                call.setup(),
                call.use(),
                ], m.mock_calls)

    def test_clone(self):
        m = Mock()
        class T1(object): pass
        class T2(object): pass
        def f1(): m.f1()
        def n1():
            m.n1()
            return T1(), T2()
        def l1(): m.l1()
        def t1(obj): m.t1()
        def t2(obj): m.t2()
        # original
        runner1 = Runner()
        runner1.add(f1, first())
        runner1.add(n1)
        runner1.add(l1, last())
        runner1.add(t1, T1)
        runner1.add(t2, T2)
        # now clone and add bits
        def f2(): m.f2()
        def n2(): m.n2()
        def l2(): m.l2()
        def tn(obj): m.tn()
        runner2 = runner1.clone()
        runner2.add(f2, first())
        runner2.add(n2)
        runner2.add(l2, last())
        # make sure types stay in order
        runner2.add(tn, T2)
        # make sure we don't allow double-adds
        runner2.add(t2)
        # now run both, and make sure we only get what we should
        runner1()
        compare([
                call.f1(),
                call.n1(),
                call.l1(),
                call.t1(),
                call.t2(),
                ], m.mock_calls)
        m.reset_mock()
        runner2()
        compare([
                call.f1(),
                call.f2(),
                call.n1(),
                call.n2(),
                call.l1(),
                call.l2(),
                call.t1(),
                call.t2(),
                call.tn()
                ], m.mock_calls)
        
class PeriodsTests(TestCase):

    def test_repr(self):
        p = Periods()
        compare(repr(p), '<Periods first:[] normal:[] last:[]>')
        
        p.first.append(1)
        p.normal.append(2)
        p.last.append(3)
        p.first.append(4)
        p.normal.append(5)
        p.last.append(6)
        compare(repr(p), '<Periods first:[1, 4] normal:[2, 5] last:[3, 6]>')

    def test_iter(self):
        p = Periods()
        compare(tuple(p), ())
        
        p.first.append(6)
        p.first.append(5)
        p.normal.append(4)
        p.normal.append(3)
        p.last.append(2)
        p.last.append(1)
        compare(tuple(p), (6, 5, 4, 3, 2, 1))