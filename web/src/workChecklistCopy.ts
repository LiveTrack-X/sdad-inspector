const en = {
  remaining: 'Other open tasks',
  checked: 'Checked tasks',
  deferred: 'Deferred tasks',
  orderNote: 'Shown in source order. This does not select or authorize the next action.',
  deferredNote: 'Kept for reference. These tasks are not current work; check the current request before resuming.',
};
type Copy = typeof en;
const ko: Copy = {
  remaining: '그 밖의 미완료 작업', checked: '체크된 작업', deferred: '보류된 작업',
  orderNote: '원문에 적힌 순서입니다. 다음 실행 순서나 승인을 뜻하지 않습니다.',
  deferredNote: '현재 진행 중인 작업이 아닙니다. 다시 시작하기 전에 현재 요청을 확인하세요.',
};
const ja: Copy = {
  remaining: 'その他の未完了タスク', checked: 'チェック済みタスク', deferred: '保留中のタスク',
  orderNote: '原文の順序です。次の操作の選択や承認を意味しません。',
  deferredNote: '参照用に保持されたタスクで、現在の作業ではありません。再開前に現在の依頼を確認してください。',
};
const zh: Copy = {
  remaining: '其他未完成任务', checked: '已勾选任务', deferred: '暂缓任务',
  orderNote: '按原文顺序显示，不代表选择或授权下一步操作。',
  deferredNote: '这些任务仅供参考，并非当前工作。恢复前请确认当前请求。',
};
export const workChecklistCopy = { en, ko, ja, 'zh-CN': zh };
