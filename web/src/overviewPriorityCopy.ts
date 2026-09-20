import type { Locale } from './i18n';

const en = {
  history: 'Git and handoff history',
  historyNote: 'Expand for repository observations and earlier checkpoints. Counts describe returned observations, not complete project history or completed work.',
  files: 'Changed files', commits: 'Recent commits', handoffs: 'Handoff records',
  partial: 'The changed-file list is partial; its total is unavailable.',
  unavailable: 'Repository observations are unavailable. This does not establish that there were no changes or commits.',
};
type Copy = typeof en;
const ko: Copy = {
  history: 'Git·핸드오프 이력',
  historyNote: '펼치면 저장소 관찰과 이전 체크포인트를 볼 수 있습니다. 개수는 반환된 관찰 기록이며 전체 프로젝트 이력이나 완료한 작업 수가 아닙니다.',
  files: '변경 파일', commits: '최근 커밋', handoffs: '핸드오프 기록',
  partial: '변경 파일 일부만 표시되어 전체 개수는 미확인입니다.',
  unavailable: '저장소 관찰을 확인할 수 없습니다. 변경이나 커밋이 없었다는 뜻은 아닙니다.',
};
const ja: Copy = {
  history: 'Git・ハンドオフ履歴',
  historyNote: '展開するとリポジトリの観察と以前のチェックポイントを確認できます。件数は取得した観察記録で、プロジェクトの全履歴や完了した作業数ではありません。',
  files: '変更ファイル', commits: '最近のコミット', handoffs: 'ハンドオフ記録',
  partial: '変更ファイルは一部のみのため、総数は不明です。',
  unavailable: 'リポジトリの観察を確認できません。変更やコミットがなかったことを示すものではありません。',
};
const zh: Copy = {
  history: 'Git 与交接历史',
  historyNote: '展开查看仓库观察和先前检查点。数量表示返回的观察记录，不代表完整项目历史或已完成工作数量。',
  files: '变更文件', commits: '最近提交', handoffs: '交接记录',
  partial: '仅显示部分变更文件，总数未知。',
  unavailable: '仓库观察不可用。这不代表没有变更或提交。',
};
export const overviewPriorityCopy: Record<Locale, Copy> = { en, ko, ja, 'zh-CN': zh };
