import React from "react";
import { useTranslation } from "react-i18next";
import { useUnifiedResumeConversationSandbox } from "./mutation/use-unified-start-conversation";
import { useUserProviders } from "./use-user-providers";
import { useVisibilityChange } from "./use-visibility-change";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { I18nKey } from "#/i18n/declaration";
import type { ConversationStatus } from "#/types/conversation-status";

interface UseSandboxRecoveryOptions {
  conversationId: string | undefined;
  conversationStatus: ConversationStatus | undefined;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

/**
 * Hook that handles sandbox recovery based on user intent.
 *
 * Recovery triggers:
 * - Page refresh: Resumes the sandbox on initial load if it was paused/stopped
 * - Tab gains focus: Resumes the sandbox if it was paused/stopped
 *
 * What does NOT trigger recovery:
 * - WebSocket disconnect: Does NOT automatically resume the sandbox
 *   (The server pauses sandboxes after 20 minutes of inactivity,
 *    and sandboxes should only be resumed when the user explicitly shows intent)
 *
 * @param options.conversationId - The conversation ID to recover
 * @param options.conversationStatus - The current conversation status
 * @param options.onSuccess - Callback when recovery succeeds
 * @param options.onError - Callback when recovery fails
 * @returns isResuming - Whether a recovery is in progress
 * @returns attemptRecovery - Function to manually trigger recovery
 */
export function useSandboxRecovery({
  conversationId,
  conversationStatus,
  onSuccess,
  onError,
}: UseSandboxRecoveryOptions) {
  const { t } = useTranslation();
  const { providers } = useUserProviders();
  const { mutate: resumeSandbox, isPending: isResuming } =
    useUnifiedResumeConversationSandbox();

  // Track if we've already attempted recovery for this conversation on initial load
  const hasAttemptedRecoveryRef = React.useRef<string | null>(null);
  const isInitialLoadRef = React.useRef(true);

  const attemptRecovery = React.useCallback(() => {
    /**
     * Only recover if the sandbox is paused (conversation.status === stopped) and not already resuming.
     *
     * Note: ConversationStatus uses different terminology than SandboxStatus:
     *   - SandboxStatus.PAUSED  → ConversationStatus.STOPPED : the runtime is not running but may be restarted
     *   - SandboxStatus.MISSING → ConversationStatus.ARCHIVED : the runtime is not running and will not restart due to deleted files.
     */
    if (!conversationId || conversationStatus !== "STOPPED" || isResuming) {
      return;
    }

    resumeSandbox(
      { conversationId, providers },
      {
        onSuccess: () => {
          onSuccess?.();
        },
        onError: (error) => {
          displayErrorToast(
            t(I18nKey.CONVERSATION$FAILED_TO_START_WITH_ERROR, {
              error: error.message,
            }),
          );
          onError?.(error);
        },
      },
    );
  }, [
    conversationId,
    conversationStatus,
    isResuming,
    providers,
    resumeSandbox,
    onSuccess,
    onError,
    t,
  ]);

  // Handle page refresh (initial load) and conversation navigation
  React.useEffect(() => {
    if (!conversationId || !conversationStatus) return;

    const isNewConversation =
      hasAttemptedRecoveryRef.current !== conversationId;

    // Reset initial load tracking when navigating to a different conversation
    if (isNewConversation && hasAttemptedRecoveryRef.current !== null) {
      isInitialLoadRef.current = true;
    }

    // Only attempt recovery on initial load, and only once per conversation
    if (isInitialLoadRef.current && isNewConversation) {
      isInitialLoadRef.current = false;
      hasAttemptedRecoveryRef.current = conversationId;

      if (conversationStatus === "STOPPED") {
        attemptRecovery();
      }
    }
  }, [conversationId, conversationStatus, attemptRecovery]);

  // Handle tab focus (visibility change) - resume when user returns to tab
  useVisibilityChange({
    conversationId: !!conversationId,
    onVisible: () => {
      if (conversationStatus === "STOPPED") {
        attemptRecovery();
      }
    },
  });

  return { isResuming, attemptRecovery };
}
