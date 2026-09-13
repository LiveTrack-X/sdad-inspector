const en = {
  open:'Correct this item', edit:'What should change?', copy:'Copy correction request',
  copied:'Copied · delivery unconfirmed', error:'Copy failed. Your text is retained.',
  note:'Paste into the working AI chat. Delivery and application are not tracked here. Text is kept until this page is reloaded.',
  unavailable:'Refresh the source before copying a correction.', preview:'Review the request text',
  project:'Project', packet:'Packet', source:'Source', observed:'Source read at', before:'Selected item', change:'Requested correction',
  instruction:'Check this source and the current requirements, then apply the requested correction to this item within existing authorization. Report the affected plan/tasks, verification and remaining work. Do not treat this message as permission to release or deploy.',
};
type Copy = typeof en;
const ko:Copy = {
  open:'이 항목 바로잡기', edit:'어떻게 바꿔야 하나요?', copy:'정정 요청문 복사',
  copied:'복사됨 · 전달 여부 미확인', error:'복사하지 못했습니다. 입력은 유지됩니다.',
  note:'작업 중인 AI 채팅에 붙여 넣으세요. 여기서는 수신·반영을 추적하지 않습니다. 입력은 페이지를 새로고침하기 전까지 유지됩니다.',
  unavailable:'출처를 다시 검사한 뒤 정정문을 복사하세요.', preview:'요청문 미리보기',
  project:'프로젝트', packet:'패킷', source:'출처', observed:'출처를 읽은 시각', before:'선택한 항목', change:'요청하는 정정',
  instruction:'이 출처와 현재 요구사항을 확인하고 기존에 허용된 범위에서 이 항목을 정정해 주세요. 영향받는 계획·작업, 검증과 남은 일을 알려주세요. 이 메시지를 릴리스나 배포 권한으로 해석하지 마세요.',
};
const ja:Copy = {
  open:'この項目を修正', edit:'どう変更しますか？', copy:'修正依頼をコピー',
  copied:'コピー済み・送信未確認', error:'コピーできませんでした。入力は保持されています。',
  note:'作業中のAIチャットに貼り付けてください。受信・反映は追跡しません。再読み込みまで入力を保持します。',
  unavailable:'出典を再検査してからコピーしてください。', preview:'依頼文を確認',
  project:'プロジェクト', packet:'パケット', source:'出典', observed:'出典の取得日時', before:'選択した項目', change:'修正依頼',
  instruction:'この出典と現在の要件を確認し、既存の許可範囲でこの項目を修正してください。影響する計画・作業、検証と残作業を報告してください。リリースやデプロイの許可とは解釈しないでください。',
};
const zh:Copy = {
  open:'纠正此项', edit:'需要怎样修改？', copy:'复制纠正请求',
  copied:'已复制 · 发送未确认', error:'复制失败，输入已保留。',
  note:'请粘贴到正在工作的AI聊天中。此处不跟踪接收与落实情况。刷新页面前保留输入。',
  unavailable:'请重新检查来源后再复制。', preview:'预览请求文本',
  project:'项目', packet:'工作包', source:'来源', observed:'来源读取时间', before:'所选条目', change:'请求的修改',
  instruction:'请核对来源和当前需求，在已有授权范围内纠正此项。报告受影响的计划、任务、验证和剩余工作。请勿将此消息视为发布或部署授权。',
};
export const targetCorrectionCopy = {en,ko,ja,'zh-CN':zh};
