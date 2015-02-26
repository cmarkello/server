"""
Tests related to exceptions
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest
import inspect

import mock

import ga4gh.frontend_exceptions as frontendExceptions
import ga4gh.backend_exceptions as backendExceptions
import ga4gh.frontend as frontend


class TestExceptionHandler(unittest.TestCase):
    """
    Test that caught exceptions are handled correctly
    """
    class UnknownException(Exception):
        pass

    class DummyFlask(object):

        def __call__(self, *args):
            return TestExceptionHandler.DummyResponse()

    class DummyResponse(object):
        pass

    def run(self, *args, **kwargs):
        # patching is required because flask.jsonify throws an exception
        # if not being called in a running app context
        dummyFlask = self.DummyFlask()
        with mock.patch('flask.jsonify', dummyFlask):
            super(TestExceptionHandler, self).run(*args, **kwargs)

    def testMappedException(self):
        for originalExceptionClass, mappedExceptionClass in \
                frontendExceptions.exceptionMap.items():
            # some exceptions require more than zero arguments to create
            numInitArgs = len(inspect.getargspec(
                originalExceptionClass.__init__).args) - 1
            args = ['arg' for _ in range(numInitArgs)]
            originalException = originalExceptionClass(*args)
            mappedException = mappedExceptionClass()
            response = frontend.handleException(originalException)
            self.assertEquals(response.status_code, mappedException.httpStatus)

    def testFrontendException(self):
        exception = frontendExceptions.ObjectNotFoundException()
        response = frontend.handleException(exception)
        self.assertEquals(response.status_code, 404)

    def testBackendException(self):
        exception = backendExceptions.CallSetNotInVariantSetException(
            'csId', 'vsId')
        response = frontend.handleException(exception)
        self.assertEquals(response.status_code, 404)

    def testUnknownExceptionBecomesServerError(self):
        exception = self.UnknownException()
        response = frontend.handleException(exception)
        self.assertEquals(response.status_code, 500)


def isClassAndExceptionSubclass(class_):
    return inspect.isclass(class_) and issubclass(class_, Exception)


class TestFrontendExceptionConsistency(unittest.TestCase):
    """
    Ensure invariants of frontend exceptions:
    - every frontend exception has a non-None error code
        - except FrontendException, which does
    - every frontend exception has a unique error code
    - every value in exceptionMap
        - is able to instantiate a new no-argument exception instance
        - derives from the base frontend exception type
    """
    def _getFrontendExceptionClasses(self):
        classes = inspect.getmembers(
            frontendExceptions, isClassAndExceptionSubclass)
        return [class_ for _, class_ in classes]

    def testCodeInvariants(self):
        codes = set()
        for class_ in self._getFrontendExceptionClasses():
            instance = class_()
            self.assertTrue(instance.code not in codes)
            codes.add(instance.code)
            if class_ == frontendExceptions.FrontendException:
                self.assertIsNone(instance.code)
            else:
                self.assertIsNotNone(instance.code)

    def testExceptionMap(self):
        for exceptionClass in frontendExceptions.exceptionMap.values():
            exception = exceptionClass()
            self.assertIsInstance(
                exception, frontendExceptions.FrontendException)


class TestBackendExceptionConsistency(unittest.TestCase):
    """
    Ensure invariants of backend exceptions:
    - every backend exception is mapped
    """
    def _getBackendExceptionClasses(self):
        classes = inspect.getmembers(
            backendExceptions, isClassAndExceptionSubclass)
        return [class_ for _, class_ in classes]

    def testBackendExceptionsMapped(self):
        for exceptionClass in self._getBackendExceptionClasses():
            self.assertTrue(exceptionClass in frontendExceptions.exceptionMap)
