const en = {
  plan: 'Plan details', openPlan: 'Show Plan details', closePlan: 'Hide Plan details',
  objective: 'Declared objective', planWork: 'Tasks explicitly marked Plan',
  noPlanWork: 'No open task is explicitly marked Plan. Read the connected documents for recorded details.',
  documents: 'Connected documents', noDocuments: 'No readable document is available in this inspection.',
  openSource: 'Open full source', taskDetails: 'Task details', source: 'Source',
  status: 'Declared task status', current: 'Current task', remaining: 'Open task', checked: 'Checked task',
  phase: 'Declared stage', unknown: 'Not declared', conflict: 'Conflicting stage markers',
  section: 'Source section', stale: 'Sources are stale or unavailable. Refresh before relying on these details.',
  planNote: 'These are repository declarations and source documents. Opening details does not execute or approve the plan.',
  openRemaining: 'Open remaining work in the full TODO',
};
type Copy = typeof en;
const ko: Copy = {
  plan: 'Plan 세부 내역', openPlan: 'Plan 세부 내역 보기', closePlan: 'Plan 세부 내역 접기',
  objective: '선언된 목표', planWork: 'Plan으로 명시된 작업',
  noPlanWork: 'Plan으로 명시된 열린 작업이 없습니다. 기록된 세부 내용은 연결 문서에서 확인할 수 있습니다.',
  documents: '연결 문서', noDocuments: '이번 검사에서 읽을 수 있는 문서가 없습니다.',
  openSource: '전체 원문 열기', taskDetails: '작업 세부 내역', source: '출처',
  status: '선언된 작업 상태', current: '현재 작업', remaining: '열린 작업', checked: '체크된 작업',
  phase: '선언된 단계', unknown: '선언되지 않음', conflict: '단계 표식 충돌',
  section: '원문 구역', stale: '출처가 오래되었거나 조회되지 않습니다. 다시 검사한 뒤 세부 내용을 확인하세요.',
  planNote: '저장소에 선언된 목표와 원문입니다. 세부 내용을 열어도 계획을 실행하거나 승인하지 않습니다.',
  openRemaining: '남은 작업 전체 TODO 열기',
};
const ja: Copy = {
  plan: 'Planの詳細', openPlan: 'Planの詳細を表示', closePlan: 'Planの詳細を閉じる',
  objective: '宣言された目標', planWork: 'Planと明示された作業',
  noPlanWork: 'Planと明示された未完了の作業はありません。記録された詳細は関連文書で確認できます。',
  documents: '関連文書', noDocuments: '今回の検査で読める文書はありません。',
  openSource: '原文全体を開く', taskDetails: '作業の詳細', source: '出典',
  status: '宣言された作業状態', current: '現在の作業', remaining: '未完了の作業', checked: 'チェック済みの作業',
  phase: '宣言された段階', unknown: '未宣言', conflict: '段階マーカーの競合',
  section: '原文のセクション', stale: '出典が古いか取得できません。再検査してから詳細を確認してください。',
  planNote: 'リポジトリの宣言と原文です。詳細を開いても計画の実行や承認は行いません。',
  openRemaining: '残りの作業をTODO原文で開く',
};
const zh: Copy = {
  plan: 'Plan详细内容', openPlan: '查看Plan详细内容', closePlan: '收起Plan详细内容',
  objective: '声明的目标', planWork: '明确标记为Plan的任务',
  noPlanWork: '没有明确标记为Plan的未完成任务。请在关联文档中查看已记录的详细内容。',
  documents: '关联文档', noDocuments: '本次检查没有可读取的文档。',
  openSource: '打开完整原文', taskDetails: '任务详细内容', source: '来源',
  status: '声明的任务状态', current: '当前任务', remaining: '未完成任务', checked: '已勾选任务',
  phase: '声明的阶段', unknown: '未声明', conflict: '阶段标记冲突',
  section: '原文章节', stale: '来源已过期或无法读取。请重新检查后再查看详细内容。',
  planNote: '这些是仓库中的声明和原文。打开详细内容不会执行或批准计划。',
  openRemaining: '在完整TODO中打开剩余任务',
};
export const workDetailCopy = {en,ko,ja,'zh-CN':zh};
