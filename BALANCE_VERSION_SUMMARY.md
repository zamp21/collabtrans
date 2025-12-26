# CollabTrans Balance版本构建总结

## 概述
成功创建了CollabTrans的balance版本，这是一个介于lite和full版本之间的平衡版本。

## 版本特点

### Balance版本 (204MB)
- ✅ **包含docling支持** - 提供强大的PDF解析能力
- ✅ **包含MinerU支持** - 核心PDF解析功能
- ✅ **包含numpy和scipy** - docling的依赖库
- ❌ **排除torch、transformers** - 避免重型AI依赖
- ❌ **排除easyocr、opencv** - 减少计算机视觉依赖
- ❌ **排除pandas、matplotlib** - 减少数据分析依赖

### 版本对比
| 版本 | 大小 | docling | MinerU | torch | 特点 |
|------|------|---------|--------|-------|------|
| Lite | 126MB | ❌ | ✅ | ❌ | 最小化，基础功能 |
| **Balance** | **204MB** | **✅** | **✅** | **❌** | **平衡版本，推荐** |
| Full | ~500MB+ | ✅ | ✅ | ✅ | 完整功能，最大 |

## 构建文件

### 新增文件
1. **`balance.spec`** - PyInstaller配置文件
2. **`build_balance.sh`** - 构建脚本
3. **`tools/build_deb.sh`** - 更新的DEB构建脚本（支持balance）

### 构建命令
```bash
# 构建balance版本
./tools/build_deb.sh --balance

# 或使用专用脚本
./build_balance.sh
```

## 安装和使用

### DEB包安装
```bash
sudo dpkg -i build/deb/collabtrans-balance_2.0.0_amd64.deb
```

### 服务管理
```bash
# 启动服务
sudo systemctl start collabtrans-balance

# 启用开机自启
sudo systemctl enable collabtrans-balance

# 检查状态
sudo systemctl status collabtrans-balance
```

### 访问服务
- 默认端口：8020
- 访问地址：http://localhost:8020

## 技术细节

### 包含的库
- **docling** - 现代PDF解析库
- **numpy** - 数值计算基础
- **scipy** - 科学计算库
- **MinerU** - PDF解析核心
- **python-docx** - DOCX处理
- **pdf2docx** - PDF转换

### 排除的库
- torch, torchvision, torchaudio
- transformers, tokenizers
- easyocr, opencv-python
- pandas, matplotlib, seaborn
- sklearn, nltk, spacy

## 推荐使用场景

### Balance版本适合：
- ✅ 需要docling PDF解析功能
- ✅ 需要MinerU PDF处理
- ✅ 希望平衡功能与大小
- ✅ 不需要重型AI模型
- ✅ 生产环境部署

### 选择建议：
- **开发测试** → Lite版本 (126MB)
- **生产部署** → **Balance版本 (204MB)** ⭐
- **完整功能** → Full版本 (500MB+)

## 构建日志
构建过程中成功收集了以下资源：
- ✅ docling相关资源
- ✅ numpy相关资源  
- ✅ scipy相关资源
- ✅ 所有必要的隐藏导入

构建时间：约2分钟
最终大小：204MB (二进制) / 200MB (DEB包)

## 总结
Balance版本成功实现了功能与大小的平衡，是生产环境部署的理想选择。它提供了完整的PDF解析能力（docling + MinerU），同时避免了重型AI依赖，保持了合理的包大小。
