#!/bin/bash

echo "=== 选择性合并 Upstream 提交 ==="
echo ""

# 检查当前状态
#if [ -n "$(git status --porcelain)" ]; then
#    echo "错误：工作目录不干净，请先提交或暂存更改"
#    exit 1
#fi

# 创建新分支
echo "创建新分支 merge-upstream-selective..."
git checkout -b merge-upstream-selective

echo ""
echo "可用的 upstream 提交："
git log --oneline upstream/main --not main

echo ""
echo "请选择要合并的提交（输入commit hash，用空格分隔）："
echo "例如：66606f0 1cdc94c 787009d"
read -p "> " commits

if [ -z "$commits" ]; then
    echo "没有选择任何提交，退出"
    git checkout main
    git branch -D merge-upstream-selective
    exit 0
fi

echo ""
echo "开始合并选定的提交..."

for commit in $commits; do
    echo "正在合并提交: $commit"
    if git cherry-pick $commit; then
        echo "✓ 成功合并 $commit"
    else
        echo "✗ 合并 $commit 时发生冲突"
        echo "请手动解决冲突后运行: git cherry-pick --continue"
        echo "或者跳过此提交: git cherry-pick --skip"
        echo "或者中止合并: git cherry-pick --abort"
        exit 1
    fi
done

echo ""
echo "所有提交合并完成！"
echo "请检查合并结果，如果满意可以运行："
echo "  git checkout main"
echo "  git merge merge-upstream-selective"
echo "  git push origin main"
