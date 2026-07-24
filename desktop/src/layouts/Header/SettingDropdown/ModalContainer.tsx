import {
  FeedbackModalContainer,
  FolderSelectorContainer,
  GlobalSearchModalContainer,
  SessionPickerModalContainer,
  VaultConsoleModalContainer,
} from "@/components/modals";

export const ModalContainer = () => {
  return (
    <>
      <FolderSelectorContainer />
      <FeedbackModalContainer />
      <GlobalSearchModalContainer />
      <SessionPickerModalContainer />
      <VaultConsoleModalContainer />
    </>
  );
};
