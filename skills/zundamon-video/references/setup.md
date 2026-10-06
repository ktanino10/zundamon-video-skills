# 音声・描画環境とMCPのセットアップ

この文書は利用者が確認して行う手順です。スキルがアプリの導入、規約同意、OS保護の解除、MCP設定変更を自動で行う権限を与えるものではありません。既存の環境があれば、重複導入しないでください。

## 必要なもの

| 用途 | 必要なもの |
| --- | --- |
| 音声の本体 | [公式VOICEVOX](https://voicevox.hiroshiba.jp/)または既存のVOICEVOX Engine |
| MCPサーバー | Node.js 20以降と、利用者が選定したVOICEVOX用MCP |
| 動画の書出し・確認 | FFmpeg / ffprobe |
| 画像・口パクの補助 | Python 3.11以降、Pillow |
| 立ち絵 | 利用者が正規の配布元から入手し、利用条件を確認したもの |

Adobe製品は必須ではありません。音声合成とファイル保存だけならffplayによる音声再生も不要です。

## 1. VOICEVOXを用意する

[公式配布](https://voicevox.hiroshiba.jp/)と[公式起動方法](https://voicevox.hiroshiba.jp/how_to_use/)を確認し、OS/CPUに合う版を選びます。配布元・版・ハッシュを確認し、初回起動と利用規約は利用者が判断してください。

macOSなどが未確認の開発元・未署名等を警告した場合、エージェントは警告を回避しません。quarantine削除、再署名、保護機能無効化などをセットアップの近道にしないでください。

本体のインストールとEngineの起動は別です。VOICEVOXの編集画面が開き、Engineが使える状態にします。標準の接続先は`http://127.0.0.1:50021`です。これをインターネットへ公開する必要はありません。

## 2. MCPを用意する

一例は、第三者製の[`@kajidog/mcp-tts-voicevox`](https://github.com/kajidog/mcp-tts-voicevox)です。VOICEVOX公式の製品ではありません。利用者がコード・依存・権限を確認して選んでください。

以下は**0.8.1**のREADMEと配布manifestに基づく例です。将来版ではオプションが変わる可能性があります。

```sh
mkdir voicevox-mcp-local
cd voicevox-mcp-local
npm init -y
npm install --save-exact @kajidog/mcp-tts-voicevox@0.8.1
```

この操作は利用者が明示的に導入を決めた場合に行います。`package-lock.json`を残し、実際の依存版を確認してください。packageの版とEngineの版は別です。

配布元と0.8.1の照合情報：

- `https://registry.npmjs.org/@kajidog/mcp-tts-voicevox/-/mcp-tts-voicevox-0.8.1.tgz`
- SHA-256: `5dc7a993cae9721bde195fb904a820d1ebe7c2f39e2cabf62b51a6a0d010d1b8`
- Node.js要件：`>=20.0.0`
- 実行入口：`node_modules/@kajidog/mcp-tts-voicevox/dist/index.js`
- MCP実装のライセンス：ISC

### ファイル生成だけの設定例

コマンドは`node`、引数は以下のように設定します。最初のパスは、自分がインストールした場所の絶対パスへ置き換えます。

```text
/ABSOLUTE/PATH/voicevox-mcp-local/node_modules/@kajidog/mcp-tts-voicevox/dist/index.js
--url
http://127.0.0.1:50021
--disable-groups
player,dictionary,apps
--disable-tools
speak,stop_speaker
--no-auto-play
```

0.8.1では`--disable-groups`と`--disable-tools`がサポートされています。この例はプレーヤー・辞書・音声再生を使わず、ping/話者一覧/ファイル生成を目的とします。登録後に実際のtool一覧を確認し、意図しないtoolが残っていれば使わず設定を見直してください。

この絞込みは、悪意あるコードを隔離するsandboxではありません。出力は自分で決めた新規作業フォルダに限定し、秘密・他人のファイル・既存音声を渡さないでください。

## 3. GitHub Copilot appへ登録する

Copilot appのCustomizeからMCP server追加を開き、Local/stdioのサーバーとして登録します。上のコマンド・引数を指定します。GUI側のPATHでNode.jsが見つからない場合は、インストール済み`node`の絶対パスを使います。既存設定を無断で上書きしないでください。

クライアントがJSON設定を受け付ける場合の同等例：

```json
{
  "mcpServers": {
    "voicevox": {
      "command": "node",
      "args": [
        "/ABSOLUTE/PATH/voicevox-mcp-local/node_modules/@kajidog/mcp-tts-voicevox/dist/index.js",
        "--url", "http://127.0.0.1:50021",
        "--disable-groups", "player,dictionary,apps",
        "--disable-tools", "speak,stop_speaker",
        "--no-auto-play"
      ]
    }
  }
}
```

設定場所や読み込み方法はクライアントごとに異なります。ClaudeやVS Code用の設定ファイルを、Copilot appへそのまま置けば動くとは限りません。

## 4. 実MCP経路を確認する

1. 接続済みのnative MCP toolを発見し、schemaを読む。
2. `voicevox_ping`相当を実呼出しし、Engineの応答を確認する。
3. `voicevox_get_speakers`相当で、**ずんだもん/ノーマル**のIDを実際に解決する。
4. `voicevox_synthesize_file`相当を、新しい出力ファイルへ呼び出す。話者と話速を明示し、勝手に再生しない。
5. 戻されたWAVの存在、形式、長さ、ハッシュを確認する。

緑の接続表示、Engineへ直接HTTPで応答があったこと、別のSDKテストの成功だけでは、このチャットからnative MCPで音声を生成できた証拠にはなりません。

discovery結果が0件でも、既に読み込まれたtoolが残っている場合があります。呼出し可能な既知schemaがあれば一度だけ確認します。見えていないtool名や引数を創作せず、同じ探索を繰り返したり、直接HTTPで生成して「MCP経由」と呼んだりしないでください。

### よくある停止点

| 状態 | 対応 |
| --- | --- |
| 本体はインストール済み、Engineに接続できない | 初回起動・確認画面・接続先を利用者が確認 |
| MCP toolがチャットに無い | クライアントの登録/再読込状態を確認。新しいサーバーを勝手に重複導入しない |
| 指定した話者/スタイルが無い | 別の声へ黙って置換せず、候補と不足を示す |
| 出力がすでに存在する | 新規batch/filenameを使う |
| PSDに未対応の効果・マスク等がある | 対応するエディターで利用者がPNG差分を出すか、追加ツールの許可を確認する |

### 公式・一次資料

- [VOICEVOX利用規約](https://voicevox.hiroshiba.jp/term/)
- [VOICEVOX Engine/API](https://github.com/VOICEVOX/voicevox_engine)
- [使用例のMCP README](https://github.com/kajidog/mcp-tts-voicevox)
- [GitHub Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
