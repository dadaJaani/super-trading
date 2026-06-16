import {
  Column,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Bot } from './bot.entity';

@Entity('trades')
export class Trade {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column('text', { name: 'bot_id' })
  botId: string;

  @ManyToOne(() => Bot, (bot) => bot.trades)
  @JoinColumn({ name: 'bot_id' })
  bot: Bot;

  @Column('text', { name: 'oanda_trade_id', nullable: true })
  oandaTradeId: string | null;

  @Column('text', { nullable: true })
  instrument: string | null;

  @Column('text', { nullable: true })
  direction: string | null;

  @Column('int', { nullable: true })
  units: number | null;

  @Column('decimal', { name: 'open_price', nullable: true })
  openPrice: string | null;

  @Column('decimal', { name: 'close_price', nullable: true })
  closePrice: string | null;

  @Column('timestamptz', { name: 'open_time', nullable: true })
  openTime: Date | null;

  @Column('timestamptz', { name: 'close_time', nullable: true })
  closeTime: Date | null;

  @Column('decimal', { nullable: true })
  pnl: string | null;

  @Column('text', { nullable: true })
  status: string | null;
}
