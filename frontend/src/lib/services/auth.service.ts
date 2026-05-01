import apiClient from "@/lib/api-client";
import type {
  DevLoginRequest,
  DevTestAccountItem,
  KakaoCallbackRequest,
  NaverCallbackRequest,
  SocialAuthRequest,
  SocialLoginResponseData,
} from "@/types";

export const authService = {
  socialLogin: (body: SocialAuthRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/social-login", body),
  kakaoCallback: (body: KakaoCallbackRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/kakao/callback", body),
  naverCallback: (body: NaverCallbackRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/naver/callback", body),
  getDevTestAccounts: () =>
    apiClient.get<DevTestAccountItem[]>("/auth/dev-test-accounts"),
  devLogin: (body: DevLoginRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/dev-login", body),
};
