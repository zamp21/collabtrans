#!/bin/bash

echo "=== Upstream Commits Review ==="
echo ""

# 获取所有upstream的提交
commits=$(git log --oneline upstream/main --not main | awk '{print $1}')

for commit in $commits; do
    echo "=== Commit: $commit ==="
    git show --stat $commit
    echo ""
    echo "--- 详细内容 ---"
    git show $commit
    echo ""
    echo "按 Enter 继续查看下一个提交，或按 Ctrl+C 退出..."
    read
done
