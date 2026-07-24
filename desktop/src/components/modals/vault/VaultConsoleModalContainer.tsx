import { useModal } from "@/contexts/modal";
import { VaultConsoleModal } from "./VaultConsoleModal";

export const VaultConsoleModalContainer = () => {
  const { isOpen, closeModal } = useModal();

  if (!isOpen("vaultConsole")) return null;

  return (
    <VaultConsoleModal
      isOpen={true}
      onClose={() => closeModal("vaultConsole")}
    />
  );
};
