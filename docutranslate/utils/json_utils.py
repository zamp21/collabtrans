import json


def flat_json_split(js: dict, chunk_size_max: int) -> list[dict]:
    """
    用给扁平的json（形如{key:val}）的分块，每个分块大小不超过chunksize字节
    """
    chunks = []
    chunk = {}
    for key, val in js.items():
        t = chunk.copy()
        t[key] = val
        chunk_size = get_json_size(t)
        if chunk_size <= chunk_size_max:
            chunk[key] = val
        else:
            chunks.append(json.dumps(chunk,ensure_ascii=False))
            chunk = {key:val}
    chunks.append(chunk)
    return chunks


def get_json_size(js: dict):
    return len(json.dumps(js,ensure_ascii=False).encode())

if __name__ == '__main__':
    js={1:2,3:4,5:"哈哈"}
    ls=flat_json_split(js,30)
    print(ls)
    # for chunk in ls:
    #     print(len(chunk.encode()))