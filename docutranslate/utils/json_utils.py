# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import json


def get_json_size(js: dict) -> int:
    """计算字典转换成JSON字符串并以UTF-8编码后的字节大小"""
    return len(json.dumps(js, ensure_ascii=False).encode('utf-8'))


def segments2json_chunks(segments: list[str], chunk_size_max: int) -> tuple[dict[str, str],
list[dict[str, str]], list[tuple[int, int]]]:
    """
    将文本段列表（segments）转换为多个JSON块。

    功能描述:
    1. 每个JSON块的格式为 {"序号0": "文本0", "序号1": "文本1", ...}。
    2. 每个JSON块经过UTF-8编码后的字节大小不超过 chunk_size_max（若单行文本就超出了chunk_size_max则保留单行文本）。
    3. 如果单个文本段本身就超过大小限制，它将被自动分割成多个子文本段。
    4. 返回值是一个元组，包含两个列表：
       - json_chunks_list: 分块后的JSON字典列表。
       - merged_indices_list: 一个元组列表，记录了被分割的文本段在新的序号系统中的起始和结束序号。
    """

    # === 第一部分：预处理，将过长的segment拆分成更小的部分 ===
    new_segments = []
    merged_indices_list = []

    for segment in segments:
        # 检查单个segment（作为一个JSON对象的值）是否已超限
        if get_json_size({len(new_segments): segment}) > chunk_size_max:
            sub_segments = []
            lines = segment.splitlines(keepends=True)
            current_sub_segment = ""
            for line in lines:
                next_sub_segment = current_sub_segment + line

                # 预估下一个子段的大小
                # 使用一个临时的key（如0）来模拟
                if get_json_size({0: next_sub_segment}) > chunk_size_max:

                    # 如果 current_sub_segment 不为空，才将其添加
                    # 这可以防止因第一行就超限而添加一个空字符串
                    if current_sub_segment:
                        sub_segments.append(current_sub_segment)
                    # 即使单行超限，也必须作为一个独立的子段添加
                    sub_segments.append(line)
                    current_sub_segment = ""  # 重置
                else:
                    current_sub_segment = next_sub_segment

            # 不要忘记循环结束后剩余的部分
            if current_sub_segment:
                sub_segments.append(current_sub_segment)

            # 如果sub_segments为空（例如，原segment为空字符串），则添加一个空字符串以保持一致性
            if not sub_segments and segment == "":
                sub_segments.append("")

            start_index = len(new_segments)
            new_segments.extend(sub_segments)
            end_index = len(new_segments)
            # 只有当一个segment被真正分割成多个部分时，才记录
            if end_index - start_index > 1:
                merged_indices_list.append((start_index, end_index))
        else:
            new_segments.append(segment)

    # === 第二部分：将处理后的 new_segments 组合成 JSON 块 ===
    json_chunks_list = []
    if not new_segments:  # 处理输入为空列表的边缘情况
        return {}, [], []

    js={}
    chunk = {}
    for key, val in enumerate(new_segments):
        # 预先构建下一个块的样子来检查大小
        prospective_chunk = chunk.copy()
        prospective_chunk[str(key)] = val

        # 检查 prospective_chunk 是否超限，并且当前 chunk 不为空
        # 如果 chunk 为空，意味着这个 val 本身就超限了，但我们必须接受它，
        # 因为它已经是最小单位了。这可以防止产生空字典。
        if get_json_size(prospective_chunk) > chunk_size_max and chunk:
            json_chunks_list.append(chunk)  # 将旧的、未超限的块存入列表
            chunk = {str(key): val}  # 用当前元素开始一个新的块
        else:
            chunk = prospective_chunk  # 未超限，更新块
        js[str(key)]=val

    # 循环结束后，将最后一个块加入列表
    if chunk:
        json_chunks_list.append(chunk)
        js.update(chunk)

    return js, json_chunks_list, merged_indices_list


if __name__ == '__main__':
    print(get_json_size({"0": ""}))
