"""Gera anuncios/<segmento>.json (4 criativos x feed + stories) a partir dos textos abaixo.
python3 -I anuncios/gerar_campanhas.py anuncios/
Depois: python3 -I kit/render_ads.py kit anuncios/<segmento>.json anuncios/"""
import json, sys, copy, pathlib

B = lambda t: f'<span class="blue">{t}</span>'
CHATBOT = {"label": "Não é chatbot pronto", "value": "É um agente construído para a sua operação"}

SEG = {
 "advocacia": dict(
  label="Para advocacia", foto="advocacia", cta="Agentes de IA sob medida para a operação do seu escritório.",
  cena=dict(title=f"Perguntou do processo? {B('Respondido na hora.')}",
    a=("Nova mensagem", "19:42", "Tem novidade no meu processo?"),
    b="Consultou o andamento e explicou a <strong>última movimentação</strong> ao cliente.",
    c=("Reunião marcada", "Ter, 15h · Dr. Paulo"), d=("Advogado avisado", "Resumo da conversa no painel.")),
  chat=dict(title=f"Quantas vezes perguntam {B('“e o meu processo?”')}", contato=("Silva Advocacia", "SA"), msgs=[
    {"from": "in", "text": "Oi, tem novidade no meu processo?", "time": "19:42"},
    {"from": "out", "text": "Oi, Marcos! Teve movimentação ontem: a audiência foi marcada.", "card": {"title": "Audiência", "sub": "12/12, 14h · Fórum central"}, "time": "19:42"},
    {"from": "in", "text": "Preciso levar algum documento?", "time": "19:43"},
    {"from": "out", "text": "Vou confirmar com o Dr. Paulo. Quer marcar uma conversa com ele?", "chips": ["Sim, quero", "Não precisa"], "time": "19:43"}]),
  split=dict(title=f"Seu advogado não precisa ser o {B('SAC do escritório.')}", rows=[
    ("Marcos A.", "Tem novidade no processo?", "19:42", "2", "Andamento enviado.", "Respondido"),
    ("Lúcia F.", "Vocês atendem trabalhista?", "20:10", "1", "Triagem feita, reunião marcada.", "Agendado"),
    ("Pedro R.", "Mandei os documentos, chegou?", "20:35", "3", "Recebidos e conferidos.", "Recebido"),
    ("Ana C.", "Posso falar com o Dr. Paulo?", "21:02", "1", "Retorno agendado amanhã.", "Agendado"),
    ("Jorge M.", "Qual o horário de vocês?", "22:18", "1", "Horários enviados.", "Respondido")]),
  st=dict(title=f"Cada escritório é único. Seu {B('agente de IA')} também.",
    checks=["Triagem do primeiro contato", "Andamento do processo ao cliente", "Coleta e conferência de documentos", "Dúvida jurídica vai para o advogado"])),

 "contabilidade": dict(
  label="Para contabilidade", foto="contabilidade", cta="Agentes de IA sob medida para a rotina da sua contabilidade.",
  cena=dict(title=f"Fechamento do mês sem {B('correr atrás')} de cliente.",
    a=("Nova mensagem", "15:01", "Segue o extrato de outubro 📎"),
    b="Conferiu os arquivos e avisou que <strong>falta 1 nota de compra</strong>.",
    c=("Tudo recebido", "Outubro · Padaria Bom Dia"), d=("Guia enviada", "DAS do mês no WhatsApp do cliente.")),
  chat=dict(title=f"Ainda cobra documento {B('cliente por cliente?')}", contato=("Lima Contabilidade", "LC"), msgs=[
    {"from": "out", "text": "Oi, Renata! Para fechar outubro, faltam:", "chips": ["Extrato bancário", "Nota de compra"], "time": "09:00"},
    {"from": "in", "text": "Segue o extrato 📎", "time": "15:01"},
    {"from": "out", "text": "Recebido e conferido ✅ Só falta a nota de compra. Te lembro amanhã cedo.", "card": {"title": "Guia do DAS", "sub": "Vence dia 20 · enviada"}, "time": "15:02"}]),
  split=dict(title=f"Seu time não precisa virar {B('cobrador de documento.')}", rows=[
    ("Renata P.", "Qual o valor da guia?", "08:12", "2", "Guia enviada.", "Enviado"),
    ("Bruno S.", "Esqueci de mandar a nota", "09:40", "1", "Lembrete agendado.", "Cobrado"),
    ("Carla D.", "Mandei o extrato, chegou?", "11:05", "3", "Recebido e conferido.", "Recebido"),
    ("Tiago L.", "Preciso da 2ª via do DAS", "14:30", "1", "2ª via enviada.", "Enviado"),
    ("Marina C.", "Como emito nota fiscal?", "17:52", "2", "Passo a passo enviado.", "Respondido")]),
  st=dict(title=f"Cada contabilidade é única. Seu {B('agente de IA')} também.",
    checks=["Cobra e confere documentos", "Envia guias e 2ª via", "Responde dúvidas recorrentes", "Exceções vão para o contador"])),

 "imobiliaria": dict(
  label="Para imobiliárias", foto="imobiliaria", cta="Agentes de IA sob medida para a operação da sua imobiliária.",
  cena=dict(title=f"Lead do anúncio às 22h. {B('Visita marcada')} às 22h.",
    a=("Novo lead", "22:07", "O apê de 2 quartos ainda está disponível?"),
    b="Confirmou o imóvel e qualificou <strong>orçamento e prazo</strong>.",
    c=("Visita agendada", "Sáb, 10h · Corretor Diego"), d=("CRM atualizado", "Lead registrado com o perfil.")),
  chat=dict(title=f"Quanto tempo seu lead {B('espera resposta?')}", contato=("Alpha Imóveis", "AI"), msgs=[
    {"from": "in", "text": "Oi! O apê de 2 quartos ainda está disponível?", "time": "22:07"},
    {"from": "out", "text": "Está sim! É para compra ou aluguel?", "chips": ["Compra", "Aluguel"], "time": "22:07"},
    {"from": "in", "text": "Aluguel, para janeiro", "time": "22:08"},
    {"from": "out", "text": "Perfeito! Agendei uma visita com o Diego.", "card": {"title": "Visita agendada", "sub": "Sáb, 10h · Rua das Flores"}, "time": "22:09"}]),
  split=dict(title=f"Lead sem resposta {B('vai para o concorrente.')}", rows=[
    ("Felipe A.", "Ainda está disponível?", "21:47", "2", "Disponível, visita sábado.", "Agendado"),
    ("Juliana R.", "Aceita pet?", "22:03", "1", "Aceita, regras enviadas.", "Respondido"),
    ("Marcos T.", "Qual o valor do condomínio?", "22:31", "1", "Valores enviados.", "Respondido"),
    ("Patrícia L.", "Dá pra visitar amanhã?", "23:10", "2", "Visita amanhã, 10h.", "Agendado"),
    ("Sérgio B.", "Têm casa com quintal?", "23:42", "1", "3 opções enviadas.", "Enviado")]),
  st=dict(title=f"Cada imobiliária é única. Seu {B('agente de IA')} também.",
    checks=["Responde o lead na hora", "Qualifica orçamento e prazo", "Agenda visitas com o corretor", "Registra tudo no seu CRM"])),

 "veterinaria": dict(
  label="Para veterinárias", foto="veterinaria", cta="Agentes de IA sob medida para a operação da sua veterinária.",
  cena=dict(title=f"Vacina vencendo? {B('Tutor já avisado.')}",
    a=("Nova mensagem", "21:30", "A vacina da Mel está vencendo?"),
    b="Consultou a ficha da Mel e sugeriu <strong>horários para a vacina</strong>.",
    c=("Vacina agendada", "Sex, 9h · Mel (V10)"), d=("Lembrete", "Enviado ao tutor na véspera.")),
  chat=dict(title=f"Seu cliente lembra da {B('vacina do pet?')}", contato=("Clínica Patas", "CP"), msgs=[
    {"from": "out", "text": "Oi, Carla! A vacina V10 da Mel vence semana que vem 🐶 Quer agendar?", "chips": ["Sim", "Depois"], "time": "10:00"},
    {"from": "in", "text": "Sim! Sexta de manhã dá?", "time": "10:12"},
    {"from": "out", "text": "Dá sim! Sexta, 9h com a Dra. Bia.", "card": {"title": "Vacina agendada", "sub": "Sex, 9h · Mel"}, "time": "10:12"}]),
  split=dict(title=f"Mais tutores atendidos, {B('menos telefone tocando.')}", rows=[
    ("Carla M.", "A vacina da Mel venceu?", "21:30", "2", "Vacina agendada.", "Agendado"),
    ("Rodrigo P.", "Tem banho e tosa sábado?", "21:55", "1", "Sábado, 10h confirmado.", "Agendado"),
    ("Fernanda L.", "Meu gato não está comendo", "22:20", "3", "Passado ao veterinário.", "Equipe"),
    ("Lucas A.", "Qual o horário de vocês?", "22:48", "1", "Horários enviados.", "Respondido"),
    ("Bianca S.", "O exame do Thor saiu?", "23:15", "1", "Resultado enviado.", "Enviado")]),
  st=dict(title=f"Cada clínica é única. Seu {B('agente de IA')} também.",
    checks=["Lembra vacinas e retornos", "Agenda consultas e banho e tosa", "Envia resultados de exames", "Urgências vão para a equipe"])),

 "estetica": dict(
  label="Para estética e beleza", foto="estetica", cta="Agentes de IA sob medida para a operação do seu espaço.",
  cena=dict(title=f"Cancelou às 23h. {B('Horário preenchido')} antes das 8h.",
    a=("Nova mensagem", "23:05", "Não vou conseguir ir amanhã às 10h 😕"),
    b="Remarcou a cliente e ofereceu o horário vago para a <strong>lista de espera</strong>.",
    c=("Horário preenchido", "Qua, 10h · Limpeza de pele"), d=("Lembrete", "Confirmação enviada na véspera.")),
  chat=dict(title=f"Quantos horários ficam {B('vazios por falta?')}", contato=("Studio Bella", "SB"), msgs=[
    {"from": "in", "text": "Preciso remarcar amanhã 😕", "time": "18:20"},
    {"from": "out", "text": "Sem problema! Tenho estes horários:", "chips": ["Qui 11h", "Sex 16h"], "time": "18:20"},
    {"from": "in", "text": "Sex 16h", "time": "18:21"},
    {"from": "out", "text": "Remarcado ✨ Te lembro na véspera.", "card": {"title": "Design de sobrancelha", "sub": "Sex, 16h · Studio Bella"}, "time": "18:21"}]),
  split=dict(title=f"Cada falta é um {B('horário perdido.')}", rows=[
    ("Júlia R.", "Preciso remarcar", "18:20", "2", "Remarcado para sexta.", "Remarcado"),
    ("Amanda S.", "Quanto é a limpeza de pele?", "19:05", "1", "Valores enviados.", "Respondido"),
    ("Paula M.", "Tem horário sábado?", "20:31", "1", "Sáb, 9h confirmado.", "Agendado"),
    ("Carol T.", "Vocês fazem micropigmentação?", "21:10", "2", "Detalhes enviados.", "Respondido"),
    ("Renata F.", "Esqueci meu horário de amanhã", "22:42", "1", "Amanhã, 14h. Até lá!", "Lembrete")]),
  st=dict(title=f"Cada espaço é único. Seu {B('agente de IA')} também.",
    checks=["Agenda e confirma horários", "Remarca e preenche cancelamentos", "Lembra a cliente na véspera", "Responde dúvidas sobre serviços"])),

 "escola": dict(
  label="Para escolas e cursos", foto="escola", cta="Agentes de IA sob medida para a rotina da sua escola.",
  cena=dict(title=f"Matrícula às 22h? {B('Visita agendada.')}",
    a=("Nova mensagem", "22:14", "Ainda tem vaga no 3º ano para 2027?"),
    b="Explicou o processo de matrícula e <strong>agendou a visita</strong> com a secretaria.",
    c=("Visita agendada", "Seg, 8h30 · Secretaria"), d=("Documentos", "Lista enviada para a família.")),
  chat=dict(title=f"Secretaria lotada {B('em época de matrícula?')}", contato=("Colégio Horizonte", "CH"), msgs=[
    {"from": "in", "text": "Oi! Preciso da 2ª via do boleto de novembro", "time": "20:05"},
    {"from": "out", "text": "Claro! Aqui está a 2ª via do Pedro:", "card": {"title": "Mensalidade novembro", "sub": "2ª via · vence dia 10"}, "time": "20:05"},
    {"from": "in", "text": "Obrigada! E a reunião de pais é quando?", "time": "20:06"},
    {"from": "out", "text": "Sábado, 9h, no auditório. Quer um lembrete na sexta?", "chips": ["Sim, por favor"], "time": "20:06"}]),
  split=dict(title=f"Sua secretaria livre das {B('perguntas repetidas.')}", rows=[
    ("Luciana P.", "2ª via do boleto?", "19:40", "2", "2ª via enviada.", "Enviado"),
    ("Ricardo L.", "Tem vaga no 3º ano?", "20:05", "1", "Visita agendada.", "Agendado"),
    ("Sandra M.", "Qual é o uniforme?", "20:48", "1", "Lista e loja enviadas.", "Respondido"),
    ("Fábio N.", "Que horas é a reunião?", "21:30", "3", "Sábado, 9h. Lembrete ativo.", "Lembrete"),
    ("Cláudia R.", "Como faço a rematrícula?", "22:12", "1", "Passo a passo enviado.", "Respondido")]),
  st=dict(title=f"Cada escola é única. Seu {B('agente de IA')} também.",
    checks=["Tira dúvidas de matrícula", "Envia boletos e 2ª via", "Avisa reuniões e eventos", "Casos delicados vão à secretaria"])),

 "oficina": dict(
  label="Para oficinas", foto="oficina", cta="Agentes de IA sob medida para a operação da sua oficina.",
  cena=dict(title=f"Perguntou do carro? {B('Respondido na hora.')}",
    a=("Nova mensagem", "16:40", "Meu carro já está pronto?"),
    b="Consultou a ordem de serviço e avisou que <strong>fica pronto às 18h</strong>.",
    c=("Orçamento aprovado", "Pastilhas de freio · Gol 2019"), d=("Revisão", "Lembrete agendado para 6 meses.")),
  chat=dict(title=f"Quantas vezes perguntam {B('“já está pronto?”')}", contato=("Auto Center Rota", "AR"), msgs=[
    {"from": "in", "text": "Boa tarde! Meu carro já está pronto?", "time": "16:40"},
    {"from": "out", "text": "Boa tarde, Carlos! Fica pronto hoje às 18h. O mecânico viu pastilhas gastas, quer incluir?", "chips": ["Incluir", "Agora não"], "time": "16:40"},
    {"from": "in", "text": "Pode incluir", "time": "16:45"},
    {"from": "out", "text": "Incluído ✅", "card": {"title": "Ordem de serviço", "sub": "Pronto hoje · 18h"}, "time": "16:45"}]),
  split=dict(title=f"Seu mecânico no carro, {B('não no WhatsApp.')}", rows=[
    ("Carlos M.", "Meu carro está pronto?", "16:40", "2", "Pronto às 18h.", "Respondido"),
    ("Fábio R.", "Quanto fica a revisão?", "17:05", "1", "Orçamento enviado.", "Enviado"),
    ("Daniel S.", "Tem horário amanhã?", "17:31", "1", "Amanhã, 8h confirmado.", "Agendado"),
    ("Luís P.", "Aprovo o orçamento", "18:10", "1", "Aprovado e registrado.", "Aprovado"),
    ("Marta G.", "Vocês fazem alinhamento?", "19:42", "2", "Sim, horários enviados.", "Respondido")]),
  st=dict(title=f"Cada oficina é única. Seu {B('agente de IA')} também.",
    checks=["Informa o status do carro", "Envia e registra orçamentos", "Agenda revisões e serviços", "Lembra a próxima revisão"])),

 "seguros": dict(
  label="Para corretoras", foto="seguros", cta="Agentes de IA sob medida para a operação da sua corretora.",
  cena=dict(title=f"Bateu o carro às 20h. {B('Sinistro encaminhado.')}",
    a=("Nova mensagem", "20:18", "Bati o carro, o que eu faço?"),
    b="Orientou o passo a passo e <strong>coletou fotos e documentos</strong> do sinistro.",
    c=("Sinistro aberto", "Protocolo enviado ao cliente"), d=("Corretor avisado", "Resumo pronto para acompanhar.")),
  chat=dict(title=f"Renovação esquecida é {B('cliente perdido.')}", contato=("Prime Seguros", "PS"), msgs=[
    {"from": "out", "text": "Oi, Eduardo! Seu seguro auto vence dia 15. Quer que eu prepare a renovação?", "chips": ["Sim", "Quero cotar"], "time": "10:00"},
    {"from": "in", "text": "Sim, mesma cobertura", "time": "10:30"},
    {"from": "out", "text": "Perfeito! Proposta enviada para o seu e-mail.", "card": {"title": "Renovação", "sub": "Seguro auto · vence dia 15"}, "time": "10:30"}]),
  split=dict(title=f"Seu corretor vendendo, {B('não emitindo 2ª via.')}", rows=[
    ("Eduardo L.", "Meu seguro vence quando?", "09:12", "1", "Dia 15. Renovação pronta.", "Respondido"),
    ("Simone A.", "2ª via do boleto?", "10:05", "2", "2ª via enviada.", "Enviado"),
    ("Rogério T.", "Bati o carro, e agora?", "20:18", "3", "Sinistro aberto.", "Aberto"),
    ("Helena C.", "Quero seguro residencial", "21:30", "1", "Dados coletados.", "Cotação"),
    ("Igor N.", "Qual é a minha franquia?", "22:41", "1", "Apólice consultada.", "Respondido")]),
  st=dict(title=f"Cada corretora é única. Seu {B('agente de IA')} também.",
    checks=["Avisa e prepara renovações", "Abre sinistros com documentos", "Envia boletos e apólices", "Negociação fica com o corretor"])),

 "condominio": dict(
  label="Para administradoras", foto="condominio", cta="Agentes de IA sob medida para a operação da sua administradora.",
  cena=dict(title=f"Reserva do salão às 22h. {B('Confirmada')} sem ligação.",
    a=("Nova mensagem", "22:02", "Quero reservar o salão de festas dia 20"),
    b="Conferiu a agenda e as regras do condomínio e <strong>confirmou a reserva</strong>.",
    c=("Reserva confirmada", "Sáb 20 · Salão de festas"), d=("Síndico avisado", "Registro no painel.")),
  chat=dict(title=f"Seu time ainda reserva {B('salão por telefone?')}", contato=("Admin Condomínios", "AC"), msgs=[
    {"from": "in", "text": "Oi! Preciso da 2ª via do condomínio", "time": "19:10"},
    {"from": "out", "text": "Claro, Regina! Apto 42, bloco B:", "card": {"title": "Condomínio novembro", "sub": "2ª via · vence dia 10"}, "time": "19:10"},
    {"from": "in", "text": "Obrigada! E a assembleia é quando?", "time": "19:11"},
    {"from": "out", "text": "Quinta, 20h, no salão. Te mando a pauta?", "chips": ["Sim, por favor"], "time": "19:11"}]),
  split=dict(title=f"Síndico e administradora {B('sem fila no WhatsApp.')}", rows=[
    ("Regina A.", "2ª via do condomínio?", "19:10", "2", "2ª via enviada.", "Enviado"),
    ("Marcelo D.", "Quero reservar a churrasqueira", "19:45", "1", "Reserva confirmada.", "Reservado"),
    ("Viviane P.", "Vazamento na garagem", "20:20", "3", "Chamado aberto.", "Chamado"),
    ("Otávio S.", "Quando é a assembleia?", "21:02", "1", "Quinta, 20h. Pauta enviada.", "Respondido"),
    ("Lia M.", "Posso fazer mudança sábado?", "21:40", "1", "Regras e horário enviados.", "Respondido")]),
  st=dict(title=f"Cada condomínio é único. Seu {B('agente de IA')} também.",
    checks=["Reservas de áreas comuns", "Boletos e 2ª via", "Chamados de manutenção", "Avisos e assembleias"])),

 "restaurante": dict(
  label="Para restaurantes", foto="restaurante", cta="Agentes de IA sob medida para a operação do seu restaurante.",
  cena=dict(title=f"Pedido às 21h? {B('Na cozinha na hora.')}",
    a=("Novo pedido", "21:12", "Quero 2 smash e uma coca, pra entrega"),
    b="Confirmou o pedido e <strong>enviou o link de pagamento</strong>.",
    c=("Pedido na cozinha", "#482 · Entrega em ~40 min"), d=("Cliente avisado", "Status enviado a cada etapa.")),
  chat=dict(title=f"Pedido no WhatsApp {B('sem atendente travado.')}", contato=("Burger da Vila", "BV"), msgs=[
    {"from": "in", "text": "Boa noite! Quero 2 smash e 1 coca, entrega", "time": "21:12"},
    {"from": "out", "text": "Boa noite! 2 Smash + 1 Coca lata. Entrego na Rua Ipê, 120?", "chips": ["Isso", "Outro endereço"], "time": "21:12"},
    {"from": "in", "text": "Isso!", "time": "21:13"},
    {"from": "out", "text": "Pedido confirmado 🍔", "card": {"title": "Pedido #482", "sub": "Na cozinha · entrega ~40 min"}, "time": "21:13"}]),
  split=dict(title=f"Sexta à noite {B('sem pedido perdido.')}", rows=[
    ("Thiago R.", "Quero 2 smash pra entrega", "21:12", "2", "Pedido #482 confirmado.", "Pedido"),
    ("Bia L.", "Vocês têm opção vegana?", "21:20", "1", "Cardápio vegano enviado.", "Respondido"),
    ("Paulo H.", "Meu pedido já saiu?", "21:34", "3", "Saiu, chega em 10 min.", "Status"),
    ("Nina F.", "Aceita Pix?", "21:41", "1", "Sim, link Pix enviado.", "Respondido"),
    ("André C.", "Qual a taxa de entrega?", "21:55", "1", "Taxa e prazo enviados.", "Respondido")]),
  st=dict(title=f"Cada restaurante é único. Seu {B('agente de IA')} também.",
    checks=["Recebe e confirma pedidos", "Integra com cardápio e caixa", "Informa o status da entrega", "Reclamações vão ao gerente"])),
}


def campanha(seg, s, foto):
    btn = "Fale com a gente"
    c = s["cena"]
    cena = {"type": "scene", "image": f"../anuncios/img/{foto}.jpg", "title": c["title"], "cards": [
        {"style": "glass", "icon": "chat", "color": "green", "app": c["a"][0], "time": c["a"][1], "text": c["a"][2]},
        {"style": "solid", "icon": "ai", "title": "Agente de IA", "tag": "Respondeu na hora", "text": c["b"]},
        {"style": "glass", "icon": "cal", "color": "blue", "app": c["c"][0], "time": "agora", "text": c["c"][1]},
        {"style": "solid", "icon": "bell", "title": c["d"][0], "text": c["d"][1]}],
        "cta": s["cta"], "button": btn}
    ch = s["chat"]
    chat = {"type": "chat", "title": ch["title"], "clock": ch["msgs"][-1]["time"],
            "contact": {"name": ch["contato"][0], "initials": ch["contato"][1], "status": "online", "tag": "Agente de IA"},
            "messages": ch["msgs"], "cta": s["cta"], "button": btn}
    sp = s["split"]
    split = {"type": "split", "title": sp["title"],
             "before": {"label": "Antes", "kpi": "Sem resposta", "rows": [{"name": r[0], "msg": r[1], "time": r[2], "badge": r[3]} for r in sp["rows"]]},
             "after": {"label": "Agente de IA", "kpi": "Respondidas", "rows": [{"name": r[0], "msg": r[4], "time": r[2], "ok": r[5]} for r in sp["rows"]]},
             "cta": s["cta"], "button": btn}
    st = {"type": "statement", "title": s["st"]["title"], "checks": s["st"]["checks"], "price": CHATBOT, "cta": s["cta"], "button": btn}
    out = []
    for nome, slide in [("cena", cena), ("conversa", chat), ("antes-depois", split), ("sob-medida", st)]:
        for fmt in ("feed", "story"):
            sl = copy.deepcopy(slide)
            if nome == "cena" and fmt == "feed":
                sl["imagePos"] = s.get("imagePos", "50% 60%")
            out.append({"slug": f"{seg}-{nome}-{fmt}", "format": fmt, "label": s["label"], "slides": [sl]})
    return out


if __name__ == "__main__":
    dest = pathlib.Path(sys.argv[1])
    escolha = json.loads((dest / "img" / "escolhidas.json").read_text(encoding="utf-8")) if (dest / "img" / "escolhidas.json").exists() else {}
    only = sys.argv[2:] or list(SEG)
    for seg in only:
        s = SEG[seg]
        e = escolha.get(seg, {})
        foto = e.get("foto", f"{s['foto']}-1")
        if "imagePos" in e: s["imagePos"] = e["imagePos"]
        (dest / f"{seg}.json").write_text(json.dumps(campanha(seg, s, foto), indent=1, ensure_ascii=False), encoding="utf-8")
        print("ok", seg, foto)
