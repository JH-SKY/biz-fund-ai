export const queryKeys = {
  business: {
    me: ["business", "me"] as const,
    finances: (bizId: string | null) =>
      ["businesses", "finance", "history", bizId] as const,
  },
  policies: {
    all: ["policies"] as const,
    list: (params: unknown) => ["policies", "list", params] as const,
    recommend: (bizId: string | null, page = 1, size = 10) =>
      ["policies", "recommend", bizId, page, size] as const,
    bookmarks: (bizId: string | null, page = 1, size = 10) =>
      ["policies", "bookmarks", bizId, page, size] as const,
    detail: (id: string) => ["policies", "detail", id] as const,
  },
  diagnoses: {
    all: ["diagnoses"] as const,
    prepare: (bizId: string | null) => ["diagnoses", "prepare", bizId] as const,
    history: (bizId: string | null) => ["diagnoses", "history", bizId] as const,
    detail: (id: string | null) => ["diagnoses", "detail", id] as const,
  },
  profile: {
    notificationSettings: ["profile", "notification-settings"] as const,
  },
};
