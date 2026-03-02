import { Settings } from "#/types/settings";
import { getProviderId } from "#/utils/map-provider";

const extractBasicFormData = (formData: FormData) => {
  const providerDisplay = formData.get("llm-provider-input")?.toString();
  const provider = providerDisplay ? getProviderId(providerDisplay) : undefined;
  const model = formData.get("llm-model-input")?.toString();

  const LLM_MODEL = `${provider}/${model}`;
  const LLM_API_KEY = formData.get("llm-api-key-input")?.toString();
  const AGENT = formData.get("agent")?.toString();
  const LANGUAGE = formData.get("language")?.toString();

  return {
    LLM_MODEL,
    LLM_API_KEY,
    AGENT,
    LANGUAGE,
  };
};

const extractAdvancedFormData = (formData: FormData) => {
  const keys = Array.from(formData.keys());
  const isUsingAdvancedOptions = keys.includes("use-advanced-options");

  let CUSTOM_LLM_MODEL: string | undefined;
  let LLM_BASE_URL: string | undefined;
  let CONFIRMATION_MODE = false;
  let SECURITY_ANALYZER: string | undefined;
  let ENABLE_DEFAULT_CONDENSER = true;

  if (isUsingAdvancedOptions) {
    CUSTOM_LLM_MODEL = formData.get("custom-model")?.toString();
    LLM_BASE_URL = formData.get("base-url")?.toString();
    CONFIRMATION_MODE = keys.includes("confirmation-mode");
    if (CONFIRMATION_MODE) {
      // only set securityAnalyzer if confirmationMode is enabled
      SECURITY_ANALYZER = formData.get("security-analyzer")?.toString();
    }
    ENABLE_DEFAULT_CONDENSER = keys.includes("enable-default-condenser");
  }

  return {
    CUSTOM_LLM_MODEL,
    LLM_BASE_URL,
    CONFIRMATION_MODE,
    SECURITY_ANALYZER,
    ENABLE_DEFAULT_CONDENSER,
  };
};

/**
 * Parses and validates a max budget per task value.
 * Ensures the value is at least 1 dollar.
 * @param value - The string value to parse
 * @returns The parsed number if valid (>= 1), null otherwise
 */
export const parseMaxBudgetPerTask = (value: string): number | null => {
  if (!value) {
    return null;
  }

  const parsedValue = parseFloat(value);
  // Ensure the value is at least 1 dollar and is a finite number
  return parsedValue && parsedValue >= 1 && Number.isFinite(parsedValue)
    ? parsedValue
    : null;
};

/**
 * Regex patterns for validating marketplace_path.
 * Supports two formats:
 * 1. Simple path: "marketplaces/default.json" or "path/to/file.json"
 * 2. Cross-repo path: "owner/repo:path/to/marketplace.json"
 */
const MARKETPLACE_PATH_SIMPLE_PATTERN =
  /^[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_.-]+)*\.json$/;
const MARKETPLACE_PATH_CROSS_REPO_PATTERN =
  /^[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+:[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_.-]+)*\.json$/;

/**
 * Validates a marketplace path value.
 * @param value - The marketplace path to validate
 * @returns true if valid or empty, false otherwise
 */
export const isValidMarketplacePath = (value: string): boolean => {
  // Empty string is valid (means no marketplace filtering)
  if (!value || value.trim() === "") {
    return true;
  }

  const trimmedValue = value.trim();

  // Security: Block path traversal and absolute paths
  if (
    trimmedValue.startsWith("/") ||
    trimmedValue.includes("..") ||
    trimmedValue.includes("\\")
  ) {
    return false;
  }

  // Check against both patterns
  return (
    MARKETPLACE_PATH_SIMPLE_PATTERN.test(trimmedValue) ||
    MARKETPLACE_PATH_CROSS_REPO_PATTERN.test(trimmedValue)
  );
};

/**
 * Parses marketplace path input.
 * @param value - The input string value
 * @returns The trimmed value if non-empty, null otherwise (null = load all skills)
 */
export const parseMarketplacePath = (
  value: string | undefined,
): string | null => {
  if (!value || value.trim() === "") {
    return null;
  }
  return value.trim();
};

export const extractSettings = (formData: FormData): Partial<Settings> => {
  const { LLM_MODEL, LLM_API_KEY, AGENT, LANGUAGE } =
    extractBasicFormData(formData);

  const {
    CUSTOM_LLM_MODEL,
    LLM_BASE_URL,
    CONFIRMATION_MODE,
    SECURITY_ANALYZER,
    ENABLE_DEFAULT_CONDENSER,
  } = extractAdvancedFormData(formData);

  return {
    llm_model: CUSTOM_LLM_MODEL || LLM_MODEL,
    llm_api_key_set: !!LLM_API_KEY,
    agent: AGENT,
    language: LANGUAGE,
    llm_base_url: LLM_BASE_URL,
    confirmation_mode: CONFIRMATION_MODE,
    security_analyzer: SECURITY_ANALYZER,
    enable_default_condenser: ENABLE_DEFAULT_CONDENSER,
    llm_api_key: LLM_API_KEY,
  };
};
