from abc import ABC, abstractmethod


class Pipeline(ABC):
    @abstractmethod
    def send_message(self):
        pass

    @abstractmethod
    def listen(self):
        pass
