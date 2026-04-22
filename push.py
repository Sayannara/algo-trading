import subprocess
import sys

# ─────────────────────────────────────────────────────────────
# 🚀 SCRIPT DE PUSH GIT RAPIDE
# ─────────────────────────────────────────────────────────────

def push():
    print("─" * 40)
    print("🚀 Git Push Helper")
    print("─" * 40)

    # Input pour le message de commit
    message = input("📝 Message de commit : ").strip()

    if not message:
        print("❌ Message vide. Annulé.")
        sys.exit(1)

    commandes = [
        ("git add .", "Ajout des fichiers..."),
        (f'git commit -m "{message}"', "Commit..."),
        ("git push", "Push vers GitHub..."),
    ]

    for cmd, label in commandes:
        print(f"\n⏳ {label}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

        if result.returncode != 0:
            print(f"❌ Erreur lors de : {cmd}")
            sys.exit(1)

    print("\n✅ Push terminé avec succès !")

if __name__ == "__main__":
    push()