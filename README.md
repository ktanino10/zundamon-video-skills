# Zundamon Video Skill

ずんだもんの解説動画を、**VOICEVOXの実MCP呼出し・許諾済みの立ち絵・実音声に基づく字幕/口パク**で作るための、非公式Agent Skillです。GitHub CopilotなどAgent Skills対応クライアントで使えます。

このリポジトリには**スキル・自作の汎用ヘルパー・合成テストだけ**を含めています。立ち絵PSD、音声モデル、生成WAV/動画、個人設定、認証情報は含みません。VOICEVOXやキャラクターの公式運営とは無関係です。

## できること

- 台本を「ボク」「〜なのだ」などの自然な口調へ整える。技術的な意味や留保は変えない。
- 実際のMCP toolを発見し、話者/スタイルを確認して新しい音声ファイルを作る。
- 新WAVの実長から字幕と章の時刻を組み直す。以前の音声の時刻を流用しない。
- 対応するPSDの口・目・腕差分を使い、音量連動の口パク、まばたき、控えめな身振りを構成する。
- 図・字幕を隠さず、胴体が画面内で不自然に切れない配置を確認する。
- 元素材、声、MCP、映像の出典・版・ハッシュと、実行した確認を分けて記録する。

**口パクのヘルパーは音量連動です。音素・母音を推定するリップシンクではありません。** PSDヘルパーも一般的なPhotoshop代替ではなく、限られた単純形式だけを扱います。

## 導入の順序

1. [セットアップガイド](docs/setup.md)に従い、VOICEVOX本体、Node.js、必要な描画ツールを用意します。
2. VOICEVOXを起動し、初回確認・OSの警告は利用者自身が判断します。
3. VOICEVOX用MCPをクライアントへ登録し、**実際のnative MCP ping/話者一覧/ファイル生成**を確認します。
4. このスキルをインストールします。
5. 自分で利用条件を確認した立ち絵と台本を渡します。

### Copilotへのスキル追加

```sh
git clone https://github.com/ktanino10/zundamon-video-skills.git
mkdir -p ~/.copilot/skills
# 同名ディレクトリがある場合は上書きせず、その内容を先に確認してください。
cp -R zundamon-video-skills/skills/zundamon-video ~/.copilot/skills/
```

プロジェクト専用なら、`skills/zundamon-video`を対象リポジトリの`.github/skills/`へコピーできます。クライアントによって再読込・新セッションが必要です。追加されただけでMCPまで接続済みにはなりません。

公式仕様：[GitHub Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

### 依頼例

> この台本をずんだもん口調の解説動画にして。音声はMCP経由だけ。添付PSDの利用条件を確認し、右側の立ち絵に口パクと軽い身振りを付けて。図と字幕を隠さず、公開せずにMP4と確認ページを保存して。

## ファイル構成

- [`skills/zundamon-video/SKILL.md`](skills/zundamon-video/SKILL.md)：実行の入口
- [`docs/setup.md`](docs/setup.md)：無料ソフトとMCP接続
- [`references/rights-and-delivery.md`](skills/zundamon-video/references/rights-and-delivery.md)：素材・クレジット・公開前の分離
- [`scripts/psd_layers.py`](skills/zundamon-video/scripts/psd_layers.py)：限定PSD読取/比較/書出し
- [`scripts/animation.py`](skills/zundamon-video/scripts/animation.py)：PCM音量からの口状態、まばたき、下端配置の検査
- `tests/`：第三者素材や実音声を使わない機能テスト
- `skills/zundamon-video/evals/`：代表依頼と期待する停止/完了条件

## 検査

Python 3.11以降とPillowが必要です。

```sh
python -m unittest discover -s tests -v
```

評価範囲は同じ作成者によるローカル機能検査と手順確認です。独立エージェントによるA/B評価、すべてのPSDやMCP実装への互換性、音声の人手による発音評価を保証しません。

## ライセンスと公開の境界

自作コード・スキル文書は[MIT](LICENSE)。VOICEVOX、MCP実装、各音声、キャラクター、立ち絵、フォントにはそれぞれ別の規約があります。このMITライセンスでそれらの権利を再許諾しているわけではありません。

スキルの実行や動画の完成は、YouTubeへのアップロード、Publicリポジトリ、GitHub Pagesへの公開の承認ではありません。公開対象・範囲・クレジットは別に確認してください。
