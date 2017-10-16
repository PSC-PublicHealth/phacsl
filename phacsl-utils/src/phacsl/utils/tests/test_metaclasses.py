import unittest

from phacsl.utils.classutils.metaclasses import ClassIsInstanceMeta

class TestClass_1(object):
    __metaclass__ = ClassIsInstanceMeta
class TestClass_2(TestClass_1):
    pass
class TestClass_3(TestClass_1):
    pass
class TestClass_4(TestClass_2):
    pass

class TestIsInstanceMeta(unittest.TestCase):

    t1 = TestClass_1()
    t2 = TestClass_2()
    t3 = TestClass_3()
    t4 = TestClass_4()

    def test_basic(self):
        self.assertTrue(self.t1.isinstance(TestClass_1))
        self.assertFalse(self.t1.isinstance(TestClass_2))
        self.assertTrue(self.t2.isinstance(TestClass_2))
        self.assertFalse(self.t3.isinstance(TestClass_2))
        self.assertTrue(self.t4.isinstance(TestClass_1))
        self.assertTrue(self.t4.isinstance(TestClass_2))
        self.assertFalse(self.t4.isinstance(TestClass_3))
        with self.assertRaises(AttributeError):
            print(object.isinstance(TestClass_1))




if __name__ == "__main__":
    unittest.main()
