import apiClient from "@/lib/api-client";
import type {
  NaverCallbackRequest,
  SocialAuthRequest,
  SocialLoginResponseData,
} from "@/types";

export const authService = {
  socialLogin: (body: SocialAuthRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/social-login", body),
  naverCallback: (body: NaverCallbackRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/naver/callback", body),
};
