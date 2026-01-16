import pytest
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from iac.orchestrator import InfrastructureOrchestrator
from iac.bucket import Bucket, BucketResult
from iac.configs import BucketConfig
from config.main import Config


@pytest.fixture
def mock_config(mock_env_vars):
    return Config.from_env()


class TestConcurrentResourceCreation:
    def test_concurrent_bucket_creation(self, mock_config):
        def create_bucket(thread_id):
            orchestrator = InfrastructureOrchestrator()
            mock_s3 = MagicMock()
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
            
            bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
            bucket_resource = Bucket(bucket_config, mock_s3)
            orchestrator.register(f"bucket_{thread_id}", bucket_resource)
            
            return orchestrator.ensure_all()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_bucket, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        assert len(results) == 5
        for result in results:
            assert len(result) == 1

    def test_concurrent_orchestrator_operations(self, mock_config):
        def run_orchestrator(thread_id):
            orchestrator = InfrastructureOrchestrator()
            mock_s3 = MagicMock()
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
            
            bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
            bucket_resource = Bucket(bucket_config, mock_s3)
            orchestrator.register(f"bucket_{thread_id}", bucket_resource)
            
            return orchestrator.ensure_all()
        
        threads = []
        results = []
        
        def worker(thread_id):
            result = run_orchestrator(thread_id)
            results.append(result)
        
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 10
        for result in results:
            assert len(result) == 1

    def test_idempotent_concurrent_creation(self, mock_config):
        mock_s3 = MagicMock()
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )
        mock_s3.create_bucket.return_value = {}
        mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
        
        bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
        bucket_resource = Bucket(bucket_config, mock_s3)
        
        def ensure_bucket():
            return bucket_resource.ensure()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(ensure_bucket) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        assert len(results) == 10
        first_arn = results[0].bucket_arn
        for result in results:
            assert result.bucket_arn == first_arn

    def test_concurrent_dependency_resolution(self, mock_config):
        def create_infrastructure(thread_id):
            orchestrator = InfrastructureOrchestrator()
            
            mock_s3 = MagicMock()
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
            
            bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
            bucket_resource = Bucket(bucket_config, mock_s3)
            orchestrator.register(f"bucket_{thread_id}", bucket_resource)
            
            return orchestrator.ensure_all()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_infrastructure, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        assert len(results) == 5
        for result in results:
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_async_concurrent_creation(self, mock_config):
        async def create_bucket_async(thread_id):
            orchestrator = InfrastructureOrchestrator()
            mock_s3 = MagicMock()
            mock_s3.head_bucket.side_effect = ClientError(
                {"Error": {"Code": "404"}}, "HeadBucket"
            )
            mock_s3.create_bucket.return_value = {}
            mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}
            
            bucket_config = BucketConfig.from_config(mock_config, mock_config.REGION_NAME)
            bucket_resource = Bucket(bucket_config, mock_s3)
            orchestrator.register(f"bucket_{thread_id}", bucket_resource)
            
            return orchestrator.ensure_all()
        
        tasks = [create_bucket_async(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for result in results:
            assert len(result) == 1
