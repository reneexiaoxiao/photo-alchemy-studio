# 本次照片转译试作 · 2026-09-15

工作流编写与新试作：Renee，AI 辅助。新增七套方法保留照片的主体线索，颜色、画幅和组合随输入变化。冰箱贴有建筑、食物、植物三类输入试作，其余各一张；这不是所有题材的稳定性保证。

## 截图参考与实现归属

用户提供的视频截图画面显示署名“动不动就饿”，可见标题为“全流程｜简约复古拼贴风格Skill分享”。截图作者身份与原版 Skill 未能通过外部链接进一步核实。公开检索未找到可以核实的原版 Skill 仓库，没有把相似仓库标为原来源。截图文件没有纳入公开仓库。

- 中式留白拼贴、邮票时刻、剪纸叙事：参考视觉方向后由 Renee 独立编写的可迁移工作流，标记为“参考再设计”。
- 厚涂微缩景观：现有 `impasto-miniature-world`（颜料小岛）覆盖相近方法，不宣称它就是截图中的原版。
- 冰箱贴、悬衡小剧场、折景明信片、画面谜语：Renee 的原创工作流实现，不主张对通用美术媒介或概念的排他权。

## 公开示例底图

三张合成测试照片沿用本项目的建筑、食物和植物样本。另三张摄影底图来自 Albert / albert-imagebook 的固定版本 `277f38d1f12a90296d11b7dc4954155821a66e6e`，保留其 MIT 许可：

- [树木街景原图](https://github.com/AlbertAZ1992/albert-imagebook/blob/277f38d1f12a90296d11b7dc4954155821a66e6e/assets/examples/source-tree-street.webp) → `assets/playful/source-tree-street.webp`
- [咖啡露台原图](https://github.com/AlbertAZ1992/albert-imagebook/blob/277f38d1f12a90296d11b7dc4954155821a66e6e/assets/examples/source-coffee-terrace.webp) → `assets/playful/source-coffee-terrace.webp`
- [日落海滩原图](https://github.com/AlbertAZ1992/albert-imagebook/blob/277f38d1f12a90296d11b7dc4954155821a66e6e/assets/examples/source-beach-sunset.webp) → `assets/playful/source-beach-sunset.webp`

[上游 MIT 许可](https://github.com/AlbertAZ1992/albert-imagebook/blob/277f38d1f12a90296d11b7dc4954155821a66e6e/LICENSE) · [随库许可副本](../assets/community-previews/licenses/albert-imagebook-MIT.txt)

示例均由内置 ImageGen 对实际底图加工生成。新工作流与本次输出按本项目 MIT 条款提供；原有第三方图片的各自许可保持不变。效果属于艺术重组，不是原照片像素保真承诺。
