from src.processing.data_stream import DataStream


def Tee(stream, amount=2):
    data = list(stream)
    return [DataStream(data) for _ in range(amount)]
