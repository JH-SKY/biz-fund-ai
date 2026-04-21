import apiClient from "@/lib/api-client";
import type { SocialAuthRequest, SocialLoginResponseData } from "@/types";

export const authService = {
  socialLogin: (body: SocialAuthRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/social-login", body),
};
