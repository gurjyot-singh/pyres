from tests import PyResTests, Basic, TestProcess, ErrorObject
from pyres import failure
from pyres.failure.base import BaseBackend
from pyres.failure.multiple import MultipleBackend
from pyres.failure.redis import RedisBackend
from pyres.job import Job

class FailureTests(PyResTests):
    def test_count(self):
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic',self.resq)
        job.fail("problem")
        assert failure.count(self.resq) == 1
        assert self.redis.llen('resque:failed') == 1

    def test_create(self):
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic',self.resq)
        e = Exception('test')
        fail = failure.create(e, 'basic', job._payload)
        assert isinstance(fail._payload, dict)
        fail.save(self.resq)
        assert failure.count(self.resq) == 1
        assert self.redis.llen('resque:failed') == 1

    def test_all(self):
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic',self.resq)
        e = Exception('problem')
        job.fail(e)
        assert len(failure.all(self.resq, 0, 20)) == 1

    def test_clear(self):
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic',self.resq)
        e = Exception('problem')
        job.fail(e)
        assert self.redis.llen('resque:failed') == 1
        failure.clear(self.resq)
        assert self.redis.llen('resque:failed') == 0

    def test_requeue(self):
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic',self.resq)
        e = Exception('problem')
        fail_object = job.fail(e)
        assert self.resq.size('basic') == 0
        failure.requeue(self.resq, fail_object)
        assert self.resq.size('basic') == 1
        job = Job.reserve('basic',self.resq)
        assert job._queue == 'basic'
        assert job._payload == {'class':'tests.Basic','args':['test1']}

# Test the MultipleBackend, basically just repeat the above tests, ensuring that
# we've delegated to the methods appropriately

class TestBackend(BaseBackend):
    def save(self, resq):
        resq.redis.set('testbackend:called', 1)

failure.backend = MultipleBackend
failure.backend.classes = [RedisBackend, TestBackend]

class MultipleFailureTests(FailureTests):
    def test_create(self):
        # Run the parent test
        FailureTests.test_create(self)
        # But also ensure the other backends were called
        assert int(self.redis.get('testbackend:called')) == 1
