/**
 * React hook for feature flags
 */

import {
  useState,
  useEffect,
  useContext,
  createContext,
  useCallback,
} from "react";
import { ConfigClient, EvaluationContext } from "../index";

interface ConfigContextValue {
  client: ConfigClient | null;
  context: EvaluationContext;
  updateContext: (newContext: Partial<EvaluationContext>) => void;
}

const ConfigContext = createContext<ConfigContextValue>({
  client: null,
  context: {},
  updateContext: () => {},
});

interface ConfigProviderProps {
  client: ConfigClient;
  initialContext?: EvaluationContext;
  children: React.ReactNode;
}

/**
 * Provider component for config client
 */
export function ConfigProvider({
  client,
  initialContext = {},
  children,
}: ConfigProviderProps) {
  const [context, setContext] = useState<EvaluationContext>(initialContext);

  const updateContext = useCallback(
    (newContext: Partial<EvaluationContext>) => {
      setContext((prev) => ({ ...prev, ...newContext }));
    },
    [],
  );

  return (
    <ConfigContext.Provider value={{ client, context, updateContext }}>
      {children}
    </ConfigContext.Provider>
  );
}

/**
 * Hook to get config client and context
 */
export function useConfig() {
  const config = useContext(ConfigContext);
  if (!config.client) {
    throw new Error("useConfig must be used within a ConfigProvider");
  }
  return config;
}

interface UseFlagResult<T = any> {
  value: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to evaluate a single feature flag
 */
export function useFlag<T = any>(
  flagKey: string,
  defaultValue?: T,
  overrideContext?: Partial<EvaluationContext>,
): UseFlagResult<T> {
  const { client, context } = useConfig();
  const [value, setValue] = useState<T | null>(defaultValue ?? null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const evaluationContext = { ...context, ...overrideContext };

  const fetchFlag = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await client.evaluateFlag(flagKey, evaluationContext);
      setValue(result ?? defaultValue ?? null);
    } catch (err) {
      setError(err as Error);
      setValue(defaultValue ?? null);
    } finally {
      setLoading(false);
    }
  }, [client, flagKey, evaluationContext, defaultValue]);

  useEffect(() => {
    fetchFlag();
  }, [fetchFlag]);

  return { value, loading, error, refetch: fetchFlag };
}

interface UseFlagsResult {
  flags: Record<string, any>;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to evaluate multiple feature flags
 */
export function useFlags(
  flagKeys: string[],
  overrideContext?: Partial<EvaluationContext>,
): UseFlagsResult {
  const { client, context } = useConfig();
  const [flags, setFlags] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const evaluationContext = { ...context, ...overrideContext };

  const fetchFlags = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await client.evaluateFlags(flagKeys, evaluationContext);
      setFlags(result);
    } catch (err) {
      setError(err as Error);
      setFlags({});
    } finally {
      setLoading(false);
    }
  }, [client, flagKeys, evaluationContext]);

  useEffect(() => {
    if (flagKeys.length > 0) {
      fetchFlags();
    }
  }, [fetchFlags]);

  return { flags, loading, error, refetch: fetchFlags };
}

/**
 * Hook to get all user flags
 */
export function useUserFlags(
  overrideContext?: Partial<EvaluationContext>,
): UseFlagsResult {
  const { client, context } = useConfig();
  const [flags, setFlags] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const evaluationContext = { ...context, ...overrideContext };

  const fetchFlags = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await client.getUserFlags(evaluationContext);
      setFlags(result);
    } catch (err) {
      setError(err as Error);
      setFlags({});
    } finally {
      setLoading(false);
    }
  }, [client, evaluationContext]);

  useEffect(() => {
    fetchFlags();
  }, [fetchFlags]);

  return { flags, loading, error, refetch: fetchFlags };
}

/**
 * Hook for chat configuration
 */
export function useChatConfig(overrideContext?: Partial<EvaluationContext>) {
  const { client, context } = useConfig();
  const [config, setConfig] = useState({
    streamingEnabled: false,
    providerOrder: ["openai", "anthropic"],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const evaluationContext = { ...context, ...overrideContext };

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await client.getChatConfig(evaluationContext);
      setConfig({
        streamingEnabled: result.streamingEnabled,
        providerOrder: result.providerOrder,
      });
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client, evaluationContext]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { config, loading, error, refetch: fetchConfig };
}

/**
 * Hook for games configuration
 */
export function useGamesConfig(overrideContext?: Partial<EvaluationContext>) {
  const { client, context } = useConfig();
  const [gamesEnabled, setGamesEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const evaluationContext = { ...context, ...overrideContext };

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await client.getGamesConfig(evaluationContext);
      setGamesEnabled(result.gamesEnabled);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [client, evaluationContext]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { gamesEnabled, loading, error, refetch: fetchConfig };
}

/**
 * Higher-order component for feature flag gating
 */
interface WithFlagProps {
  flagKey: string;
  fallback?: React.ComponentType<any>;
  context?: Partial<EvaluationContext>;
}

export function withFlag<P extends object>(
  Component: React.ComponentType<P>,
  flagKey: string,
  fallback?: React.ComponentType<P>,
) {
  return function WrappedComponent(
    props: P & { context?: Partial<EvaluationContext> },
  ) {
    const { context, ...componentProps } = props;
    const { value, loading } = useFlag<boolean>(flagKey, false, context);

    if (loading) {
      return null; // or loading spinner
    }

    if (value) {
      return <Component {...(componentProps as P)} />;
    }

    if (fallback) {
      const FallbackComponent = fallback;
      return <FallbackComponent {...(componentProps as P)} />;
    }

    return null;
  };
}

/**
 * Component for conditional rendering based on flag
 */
interface FlagGateProps {
  flagKey: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  context?: Partial<EvaluationContext>;
}

export function FlagGate({
  flagKey,
  children,
  fallback,
  context,
}: FlagGateProps) {
  const { value, loading } = useFlag<boolean>(flagKey, false, context);

  if (loading) {
    return null;
  }

  if (value) {
    return <>{children}</>;
  }

  return <>{fallback || null}</>;
}

export type { EvaluationContext };
