const en = {
  open:'Correct this item', edit:'What should change?', copy:'Copy correction request',
  copied:'Copied · delivery unconfirmed', error:'Copy failed. Your text is retained.',
  note:'Paste into the working AI chat. Delivery and application are not tracked here. Text is kept until this page is reloaded.',
  unavailable:'Refresh the source before copying a correction.', preview:'Review the request text',
  previousDrafts:'Previous draft', recoveryNotice:'A draft from another source revision is retained. Compare the selected item and source before carrying it forward; nothing is applied automatically.',
  previousSource:'Previous selected source', currentSource:'Current selected source', previousText:'Previous correction text',
  itemUnchanged:'The selected item text is unchanged; other source content or its revision may have changed.', itemChanged:'The selected item text changed. The same source location does not guarantee it is still the same item.',
  usePrevious:'Use this draft with the current source', keepCurrent:'Current input is preserved. Clear it explicitly before using a previous draft.',
  documentDrafts:'Other saved drafts in this document', documentRecoveryNotice:'These drafts belong to other source locations in the same document and packet. A line may have moved, or this may be a different item. Compare and choose manually; no correspondence is assumed.', locationChanged:'The source location differs. Confirm which item this draft belongs to before using it here.',
  project:'Project', packet:'Packet', source:'Source', observed:'Source read at', before:'Selected item', change:'Requested correction',
  instruction:'Check this source and the current requirements, then apply the requested correction to this item within existing authorization. Report the affected plan/tasks, verification and remaining work. Do not treat this message as permission to release or deploy.',
};
type Copy = typeof en;
const ko:Copy = {
  open:'이 항목 바로잡기', edit:'어떻게 바꿔야 하나요?', copy:'정정 요청문 복사',
  copied:'복사됨 · 전달 여부 미확인', error:'복사하지 못했습니다. 입력은 유지됩니다.',
  note:'작업 중인 AI 채팅에 붙여 넣으세요. 여기서는 수신·반영을 추적하지 않습니다. 입력은 페이지를 새로고침하기 전까지 유지됩니다.',
  unavailable:'출처를 다시 검사한 뒤 정정문을 복사하세요.', preview:'요청문 미리보기',
  previousDrafts:'이전 초안', recoveryNotice:'다른 출처 버전에서 작성한 초안이 남아 있습니다. 선택한 항목과 출처를 비교한 뒤 직접 가져오세요. 자동으로 반영하지 않습니다.',
  previousSource:'이전에 선택한 출처', currentSource:'현재 선택한 출처', previousText:'이전 정정문',
  itemUnchanged:'선택한 항목의 문구는 같습니다. 출처의 다른 내용이나 버전이 바뀌었을 수 있습니다.', itemChanged:'선택한 항목의 문구가 바뀌었습니다. 출처 위치가 같아도 같은 항목이라는 뜻은 아닙니다.',
  usePrevious:'현재 출처에 이 초안 가져오기', keepCurrent:'현재 입력을 유지합니다. 이전 초안을 가져오려면 현재 입력을 직접 지우세요.',
  documentDrafts:'이 문서에 저장된 다른 초안', documentRecoveryNotice:'같은 문서·패킷의 다른 출처 위치에서 작성한 초안입니다. 줄이 이동했거나 다른 항목일 수 있습니다. 자동 연결하지 않으니 직접 비교하고 선택하세요.', locationChanged:'출처 위치가 다릅니다. 이 초안이 어느 항목에 해당하는지 확인한 뒤 가져오세요.',
  project:'프로젝트', packet:'패킷', source:'출처', observed:'출처를 읽은 시각', before:'선택한 항목', change:'요청하는 정정',
  instruction:'이 출처와 현재 요구사항을 확인하고 기존에 허용된 범위에서 이 항목을 정정해 주세요. 영향받는 계획·작업, 검증과 남은 일을 알려주세요. 이 메시지를 릴리스나 배포 권한으로 해석하지 마세요.',
};
const ja:Copy = {
  open:'この項目を修正', edit:'どう変更しますか？', copy:'修正依頼をコピー',
  copied:'コピー済み・送信未確認', error:'コピーできませんでした。入力は保持されています。',
  note:'作業中のAIチャットに貼り付けてください。受信・反映は追跡しません。再読み込みまで入力を保持します。',
  unavailable:'出典を再検査してからコピーしてください。', preview:'依頼文を確認',
  previousDrafts:'以前の下書き', recoveryNotice:'別の出典バージョンの下書きが残っています。選択項目と出典を比較してから引き継いでください。自動では適用しません。',
  previousSource:'以前選択した出典', currentSource:'現在選択した出典', previousText:'以前の修正文',
  itemUnchanged:'選択項目の文言は同じです。出典の他の内容やバージョンが変わった可能性があります。', itemChanged:'選択項目の文言が変わりました。同じ出典位置でも同じ項目とは限りません。',
  usePrevious:'現在の出典にこの下書きを引き継ぐ', keepCurrent:'現在の入力を保持します。以前の下書きを使う場合は現在の入力を明示的に消してください。',
  documentDrafts:'この文書の他の保存済み下書き', documentRecoveryNotice:'同じ文書・パケットの別の出典位置で作成された下書きです。行が移動した場合も別項目の場合もあります。対応を推測せず、手動で比較して選択してください。', locationChanged:'出典位置が異なります。どの項目の下書きか確認してから引き継いでください。',
  project:'プロジェクト', packet:'パケット', source:'出典', observed:'出典の取得日時', before:'選択した項目', change:'修正依頼',
  instruction:'この出典と現在の要件を確認し、既存の許可範囲でこの項目を修正してください。影響する計画・作業、検証と残作業を報告してください。リリースやデプロイの許可とは解釈しないでください。',
};
const zh:Copy = {
  open:'纠正此项', edit:'需要怎样修改？', copy:'复制纠正请求',
  copied:'已复制 · 发送未确认', error:'复制失败，输入已保留。',
  note:'请粘贴到正在工作的AI聊天中。此处不跟踪接收与落实情况。刷新页面前保留输入。',
  unavailable:'请重新检查来源后再复制。', preview:'预览请求文本',
  previousDrafts:'以前的草稿', recoveryNotice:'已保留其他来源版本的草稿。请对比所选条目和来源，再手动沿用；不会自动应用。',
  previousSource:'以前选择的来源', currentSource:'当前选择的来源', previousText:'以前的纠正文本',
  itemUnchanged:'所选条目文本未变；来源的其他内容或版本可能已更改。', itemChanged:'所选条目文本已变。来源位置相同并不保证仍是同一条目。',
  usePrevious:'将此草稿沿用于当前来源', keepCurrent:'当前输入已保留。请先明确清空当前输入，再使用以前的草稿。',
  documentDrafts:'此文档中其他已保存的草稿', documentRecoveryNotice:'这些草稿来自同一文档和工作包中的其他来源位置。可能是行号变化，也可能是不同条目。不会推断对应关系，请手动比较并选择。', locationChanged:'来源位置不同。请确认此草稿属于哪个条目后，再在此处使用。',
  project:'项目', packet:'工作包', source:'来源', observed:'来源读取时间', before:'所选条目', change:'请求的修改',
  instruction:'请核对来源和当前需求，在已有授权范围内纠正此项。报告受影响的计划、任务、验证和剩余工作。请勿将此消息视为发布或部署授权。',
};
export const targetCorrectionCopy = {en,ko,ja,'zh-CN':zh};
