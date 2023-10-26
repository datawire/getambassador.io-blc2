import codecs


class Encoding(object):
    name: str
    codec_info: codecs.CodecInfo

    def __init__(self, name: str, codec_info: codecs.CodecInfo) -> None:
        self.name = name

    def __repr__(self) -> str:
        return '<Encoding %s>' % self.name
