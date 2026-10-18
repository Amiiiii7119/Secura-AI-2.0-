from abc import ABC, abstractmethod
from typing import List, Tuple
from app.schemas.evidence import BranchForensicResult, SuspiciousTemporalInterval
from app.services.video_sampler import SamplingResult

class BaseVideoBranch(ABC):
    def __init__(self, analyzer_id: str, method: str):
        self.analyzer_id = analyzer_id
        self.method = method

    @abstractmethod
    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        pass
