from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError, retry_if_not_exception_type
from agentforge.logger import AgentLogger
import time

class CircuitOpenError(RuntimeError):
    pass

class CircuitBreaker:
    def __init__(self, max_failures=3, reset_timeout = 60):
        self._failures = 0
        self._max = max_failures
        self._reset = reset_timeout
        self._open_at = None
        self._open = False

    def call_succeeded(self): 
        self._failures = 0
        self._open = False

    def call_failed(self):
        self._failures += 1
        if self._failures >= self._max:
            self._open = True
            self._open_at = time.monotonic()

    def is_open(self) -> bool:
        if self._open:
            elapsed = time.monotonic() - self._open_at
            if elapsed > self._reset:
                self._open = False # half-open: allow one probe
        return self._open


class BaseMCPServer(ABC):
    '''
    Abstract base for all MCP servers.
    Each subclass wraps one external API and exposes clean tool methods.
    Built-in: retry (3x, exponential backoff) + circuit breaker.
    '''

    def __init__(self, name: str):
        self.name = name
        self.logger = AgentLogger(name)
        self._circuit = CircuitBreaker()

    @abstractmethod
    def health_check(self) -> bool:
        ...
        
    def _log_call(self, action: str):
        self.logger.mcp_call(self.name, action=action)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True, retry=retry_if_not_exception_type(CircuitOpenError))
    def _resilient_get(self, client, url, **kwargs):
        if self._circuit.is_open():
            raise CircuitOpenError(f'Circuit open for {self.name} - skipping call')
        
        try:
            r = client.get(url, **kwargs)
            r.raise_for_status()
            self._circuit.call_succeeded()
            return r
            
        except CircuitOpenError:
            raise
        except Exception as e:
            self._circuit.call_failed()
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True, retry=retry_if_not_exception_type(CircuitOpenError))
    def _resilient_post(self, client, url, **kwargs):
        if self._circuit.is_open():
            raise CircuitOpenError(f'Circuit open for {self.name} - skipping call')
        
        try:
            r = client.post(url, **kwargs)
            r.raise_for_status()
            self._circuit.call_succeeded()
            return r
            
        except CircuitOpenError:
            raise
        except Exception as e:
            self._circuit.call_failed()
            raise
