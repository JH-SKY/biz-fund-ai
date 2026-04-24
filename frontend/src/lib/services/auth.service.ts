import apiClient from "@/lib/api-client";
import type {
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
};
