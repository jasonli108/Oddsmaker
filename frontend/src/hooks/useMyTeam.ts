import { api } from '../api/client';
import type { Team } from '../api/types';
import { useEvent } from './useEvent';
import { usePolling } from './usePolling';
import { useUser } from './useUser';

/**
 * The team this player signed up in the current event, if they have. Each player can sign up
 * one team, so once this is set the sign-up form is closed to them.
 */
export function useMyTeam(): Team | undefined {
  const { slug } = useEvent();
  const { user } = useUser();
  const teams = usePolling(
    () => (slug && user ? api.listTeams(slug) : Promise.resolve([])),
    `my-team-${slug}-${user?.id}`,
  );
  return user ? teams.data?.find((t) => t.creator_user_id === user.id) : undefined;
}
