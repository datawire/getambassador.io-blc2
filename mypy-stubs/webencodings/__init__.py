import codecs


class Encoding(object):
    name: str
    codec_info: codecs.CodecInfo

    def __init__(self, name: str, codec_info: codecs.CodecInfo) -> None:
        ...

    def __repr__(self) -> str:
        ...
