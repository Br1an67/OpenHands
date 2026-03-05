import React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useFeatureFlagEnabled } from "posthog-js/react";
import { ContextMenu } from "#/ui/context-menu";
import { ContextMenuListItem } from "./context-menu-list-item";
import { ContextMenuCTA } from "./context-menu-cta";
import { Divider } from "#/ui/divider";
import { useClickOutsideElement } from "#/hooks/use-click-outside-element";
import { I18nKey } from "#/i18n/declaration";
import LogOutIcon from "#/icons/log-out.svg?react";
import DocumentIcon from "#/icons/document.svg?react";
import PlusIcon from "#/icons/plus.svg?react";
import { useSettingsNavItems } from "#/hooks/use-settings-nav-items";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { useTracking } from "#/hooks/use-tracking";

interface AccountSettingsContextMenuProps {
  onLogout: () => void;
  onClose: () => void;
}

export function AccountSettingsContextMenu({
  onLogout,
  onClose,
}: AccountSettingsContextMenuProps) {
  const ref = useClickOutsideElement<HTMLDivElement>(onClose);
  const { t } = useTranslation();
  const { trackAddTeamMembersButtonClick } = useTracking();
  const { data: config } = useConfig();
  const { data: settings } = useSettings();
  const isAddTeamMemberEnabled = useFeatureFlagEnabled(
    "exp_add_team_member_button",
  );
  // Get navigation items and filter out LLM settings if the feature flag is enabled
  const items = useSettingsNavItems();

  const isSaasMode = config?.app_mode === "saas";
  const hasAnalyticsConsent = settings?.user_consents_to_analytics === true;
  const showAddTeamMembers =
    isSaasMode && isAddTeamMemberEnabled && hasAnalyticsConsent;

  const navItems = items.map((item) => ({
    ...item,
    icon: React.cloneElement(item.icon, {
      width: 16,
      height: 16,
    } as React.SVGProps<SVGSVGElement>),
  }));
  const handleNavigationClick = () => onClose();

  const handleAddTeamMembers = () => {
    trackAddTeamMembersButtonClick();
    onClose();
  };

  return (
    <div
      ref={ref}
      data-testid="account-settings-context-menu"
      className="absolute bg-tertiary rounded-[20px] border border-[#525252] text-white overflow-hidden z-[9999] context-menu-box-shadow mt-2 right-0 md:right-full md:left-full md:bottom-0 ml-0 w-[734px] h-[487px] flex flex-row gap-6 p-[30px]"
    >
      {/* Left column - Settings list */}
      <ContextMenu
        testId="account-settings-menu-list"
        className="relative !bg-transparent !shadow-none !rounded-none border-none p-0 m-0 w-[320px] [box-shadow:none]"
      >
        {showAddTeamMembers && (
          <ContextMenuListItem
            testId="add-team-members-button"
            onClick={handleAddTeamMembers}
            className="flex items-center gap-2 p-2 hover:bg-[#5C5D62] rounded h-[30px]"
          >
            <PlusIcon width={16} height={16} />
            <span className="text-white text-sm">
              {t(I18nKey.SETTINGS$NAV_ADD_TEAM_MEMBERS)}
            </span>
          </ContextMenuListItem>
        )}
        {navItems.map(({ to, text, icon }) => (
          <Link key={to} to={to} className="text-decoration-none">
            <ContextMenuListItem
              onClick={handleNavigationClick}
              className="flex items-center gap-2 p-2 hover:bg-[#5C5D62] rounded h-[30px]"
            >
              {icon}
              <span className="text-white text-sm">{t(text)}</span>
            </ContextMenuListItem>
          </Link>
        ))}

        <Divider />

        <a
          href="https://docs.openhands.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="text-decoration-none"
        >
          <ContextMenuListItem
            onClick={onClose}
            className="flex items-center gap-2 p-2 hover:bg-[#5C5D62] rounded h-[30px]"
          >
            <DocumentIcon width={16} height={16} />
            <span className="text-white text-sm">
              {t(I18nKey.SIDEBAR$DOCS)}
            </span>
          </ContextMenuListItem>
        </a>

        <ContextMenuListItem
          onClick={onLogout}
          className="flex items-center gap-2 p-2 hover:bg-[#5C5D62] rounded h-[30px]"
        >
          <LogOutIcon width={16} height={16} />
          <span className="text-white text-sm">
            {t(I18nKey.ACCOUNT_SETTINGS$LOGOUT)}
          </span>
        </ContextMenuListItem>
      </ContextMenu>

      {/* Right column - CTA */}
      <ContextMenuCTA />
    </div>
  );
}
