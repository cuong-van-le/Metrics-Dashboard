import pytest
import time
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from iac.orchestrator import InfrastructureOrchestrator
from iac.base import Resource, ResourceResult
from iac.bucket import Bucket
from iac.configs import BucketConfig
from config.main import Config


class MockSlowResource(Resource[ResourceResult]):
    def __init__(self, delay: float = 0.1):
        super().__init__(config={}, client=MagicMock())
        self.delay = delay
    
    def _get_resource_name(self) -> str:
        return "mock-resource"
    
    def _exists(self, name: str) -> bool:
        return False
    
    def _handle_existing(self, name: str) -> ResourceResult:
        return ResourceResult()
    
    def _create(self, name: str) -> ResourceResult:
        time.sleep(self.delay)
        return ResourceResult()


@pytest.fixture
def mock_config(mock_env_vars):
    return Config.from_env()


class TestPerformance:
    @pytest.mark.benchmark
    def test_orchestrator_performance(self, benchmark, mock_config):
        def setup():
            orchestrator = InfrastructureOrchestrator()
            mock_s3 = MagicMock()
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
            
            bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
            bucket_resource = Bucket(bucket_config, mock_s3)
            orchestrator.register("bucket", bucket_resource)
            return (orchestrator,), {}
        
        def run(orchestrator):
            return orchestrator.ensure_all()
        
        result = benchmark.pedantic(run, setup=setup, rounds=10, iterations=1)
        assert "bucket" in result

    @pytest.mark.benchmark
    def test_resource_creation_overhead(self, benchmark):
        resource = MockSlowResource(delay=0.01)
        
        def run():
            return resource.ensure()
        
        result = benchmark.pedantic(run, rounds=100, iterations=1)
        assert result is not None

    def test_sequential_vs_parallel_creation(self, mock_config):
        orchestrator = InfrastructureOrchestrator()
        
        slow_resource1 = MockSlowResource(delay=0.1)
        slow_resource2 = MockSlowResource(delay=0.1)
        
        orchestrator.register("resource1", slow_resource1)
        orchestrator.register("resource2", slow_resource2)
        
        start = time.time()
        results = orchestrator.ensure_all()
        elapsed = time.time() - start
        
        assert "resource1" in results
        assert "resource2" in results
        assert elapsed < 0.25

    def test_large_dependency_graph_performance(self, mock_config):
        orchestrator = InfrastructureOrchestrator()
        
        resources = []
        for i in range(10):
            resource = MockSlowResource(delay=0.01)
            orchestrator.register(f"resource{i}", resource)
            resources.append(resource)
        
        start = time.time()
        results = orchestrator.ensure_all()
        elapsed = time.time() - start
        
        assert len(results) == 10
        assert elapsed < 0.5

    @pytest.mark.benchmark
    def test_validation_performance(self, benchmark):
        from iac.validation import ResourceValidator
        
        test_names = [
            "test-bucket-name-123",
            "test_lambda_function",
            "test-role-name",
            "test-firehose-stream",
        ] * 100
        
        def run():
            for name in test_names:
                ResourceValidator.validate_bucket_name(name)
                ResourceValidator.validate_lambda_name(name)
                ResourceValidator.validate_role_name(name)
                ResourceValidator.validate_firehose_stream_name(name)
        
        benchmark(run)
