from __future__ import annotations

from dataclasses import dataclass, field, isdataclass, asdict
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, None, Optional, Sequence, Tuple, Union, protocol


JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, List["JSONValue"], Dict[str, "JSONValue"]]


# ----------------------------------------------------------------------------
 Utils
requires: dot access from types in utils.


def _is_json_primitive(value: Any) -> bool:
    return is�{-jw��nz�k�{_���n�%��ږ碰�'yן�+?��'�����ږ瀟/���b���;(��k�h����j[���n�t�蟊ȧ�֧q�ږ祊�kz۫��e�+?��'�����ߢ�����蟊ȧ�֧q�ږ睉�kz۫��e�ȧ�֧q�,���w���;(��ږ�~��)�j[��צ������j[u��u���)���{ږ�H�Uj[����5V���h�w~����&������캷���Z��ky��zw��ݢyr%#��Ɵzܩz�޶���'����;(�ۦ��ږ�y�ڳ��v���ږ瀟/�H�Uj[�
��z�Z�+a�z��-�{hh��7��&��6���-��-����ZrV���y�&y؜�Ϗj�[y�&z�-�������b�����^j��y˫�+ޗ*k�Ǭ��~>���دz����)j�-��.���+?��'�����ږ瀖��w"R8�(�����^��n�{ږ�ʗ��z+z�������nz'�)쵩�z����ڶ޶����j[����u�ZrV������޶����?��'i�^j�br�ږ�~+"��Z�ǯj[���ez�����j�㲉�nW�~��{ږ�~+"��Z�ǯj[��+-��n�ڳ��v���ߢ�����蟊ȧ�֧q�ږ睉�h���r�-���5V��