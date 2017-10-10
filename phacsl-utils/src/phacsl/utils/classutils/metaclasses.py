from collections import defaultdict
class ClassIsInstanceMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, '_setofclasses'):
            cls._setofclasses = defaultdict(set)
        cls._setofclasses[cls.__name__].add(cls.__name__)
        def recurse_class_hierarchy(cls):
            class_list = [cls.__name__]
            for base_ in cls.__bases__:
                class_list.extend(recurse_class_hierarchy(base_))
            return class_list
        for c in recurse_class_hierarchy(cls):
            cls._setofclasses[cls.__name__].add(c)
        def isinstance(self, cls_):
            cls_str = cls_.__name__
            if cls_str in self.__class__._setofclasses[self.__class__.__name__]:
                return True
            else:
                return False
        cls.isinstance = isinstance
        super(ClassIsInstanceMeta, cls).__init__(name, bases, dct)

    @classmethod
    def _test(cls):
        class TestClass_1(object):
            __metaclass__ = ClassIsInstanceMeta
        class TestClass_2(TestClass_1):
            pass
        class TestClass_3(TestClass_1):
            pass
        class TestClass_4(TestClass_2):
            pass

        t1 = TestClass_1()
        t2 = TestClass_2()
        t3 = TestClass_3()
        t4 = TestClass_4()

        print(t1.isinstance(TestClass_1))
        print(t1.isinstance(TestClass_2))
        print(t2.isinstance(TestClass_2))
        print(t3.isinstance(TestClass_2))
        print(t4.isinstance(TestClass_1))
        print(t4.isinstance(TestClass_2))
        print(t4.isinstance(TestClass_3))
        try:
            print(object.isinstance(TestClass_1))
        except AttributeError:
            print("NOTE: if the class (or one of its bases) doesn't use the ClassIsInstanceMeta metaclass, an exception is raised")
