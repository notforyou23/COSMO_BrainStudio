import re

class ValidationError(Exception):
    def __init__(self, message, path=""):
        super().__init__(message)
        self.message = message
        self.path = path or ""
    def __str__(self):
        return f"{self.path}: {self.message}" if self.path else self.message

def _is_type(x, t):
    if t == "null": return x is None
    if t == "boolean": return isinstance(x, bool)
    if t == "integer": return isinstance(x, int) and not isinstance(x, bool)
    if t == "number": return (isinstance(x, (int, float)) and not isinstance(x, bool))
    if t == "string": return isinstance(x, str)
    if t == "array": return isinstance(x, list)
    if t == "object": return isinstance(x, dict)
    return False

def _path(p, key):
    if key is None: return p
    if isinstance(key, int): return f"{p}[{key}]" if p else f"[{key}]"
    if key == "": return p
    return f"{p}.{key}" if p else str(key)

def validate(instance, schema, path=""):
    for err in iter_errors(instance, schema, path):
        raise err
    return True

def iter_errors(instance, schema, path=""):
    if schema is None:
        return
        yield  # pragma: no cover
    if not isinstance(schema, dict):
        yield ValidationError("schema must be an object", path); return

    t = schema.get("type")
    if t is not None:
        ok = any(_is_type(instance, tt) for tt in t) if isinstance(t, list) else _is_type(instance, t)
        if not ok:
            yield ValidationError(f"expected type {t}", path); return

    if "const" in schema and instance != schema["const"]:
        yield ValidationError("value must equal const", path)

    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or instance not in enum:
            yield ValidationError("value not in enum", path)

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            yield ValidationError("string shorter than minLength", path)
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            yield ValidationError("string longer than maxLength", path)
        if "pattern" in schema:
            pat = schema["pattern"]
            try:
                if re.search(pat, instance) is None:
                    yield ValidationError("string does not match pattern", path)
            except re.error:
                yield ValidationError("invalid regex pattern in schema", path)

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            yield ValidationError("number less than minimum", path)
        if "maximum" in schema and instance > schema["maximum"]:
            yield ValidationError("number greater than maximum", path)
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            yield ValidationError("number not greater than exclusiveMinimum", path)
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            yield ValidationError("number not less than exclusiveMaximum", path)

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            yield ValidationError("array shorter than minItems", path)
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            yield ValidationError("array longer than maxItems", path)
        if "items" in schema:
            items_s = schema["items"]
            if isinstance(items_s, dict):
                for i, v in enumerate(instance):
                    yield from iter_errors(v, items_s, _path(path, i))
            elif isinstance(items_s, list):
                for i, s in enumerate(items_s):
                    if i >= len(instance): break
                    yield from iter_errors(instance[i], s, _path(path, i))

    if isinstance(instance, dict):
        req = schema.get("required")
        if isinstance(req, list):
            for k in req:
                if k not in instance:
                    yield ValidationError(f"missing required property '{k}'", path)

        props = schema.get("properties")
        if isinstance(props, dict):
            for k, s in props.items():
                if k in instance:
                    yield from iter_errors(instance[k], s, _path(path, k))

        addl = schema.get("additionalProperties", True)
        if addl is not True:
            known = set(props.keys()) if isinstance(props, dict) else set()
            for k in instance.keys():
                if k in known: continue
                if addl is False:
                    yield ValidationError(f"additional property '{k}' not allowed", _path(path, k))
                elif isinstance(addl, dict):
                    yield from iter_errors(instance[k], addl, _path(path, k))

    for kw in ("allOf", "anyOf", "oneOf"):
        subs = schema.get(kw)
        if isinstance(subs, list) and subs:
            results = []
            for s in subs:
                errs = list(iter_errors(instance, s, path))
                results.append(errs)
            if kw == "allOf":
                for errs in results:
                    for e in errs: yield e
            elif kw == "anyOf":
                if all(results):  # all have errors
                    yield ValidationError("does not satisfy anyOf", path)
            elif kw == "oneOf":
                ok_count = sum(1 for errs in results if not errs)
                if ok_count != 1:
                    yield ValidationError("does not satisfy oneOf", path)

    if "not" in schema and isinstance(schema["not"], dict):
        if not list(iter_errors(instance, schema["not"], path)):
            yield ValidationError("must not be valid against 'not' schema", path)
